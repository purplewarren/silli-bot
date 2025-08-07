"""
Proactive Scheduler
Handles proactive insights and reasoning toggle integration
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from loguru import logger
from .profiles import profiles
from .families import families
from .storage import storage
from .reason_client import create_reasoner_config, get_reasoner_response
from .i18n import get_locale


class ProactiveScheduler:
    """Handles proactive insights and reasoning integration."""
    
    def __init__(self, interval_hours: int = 3, max_insights_per_family: int = 1):
        self.interval_hours = interval_hours
        self.max_insights_per_family = max_insights_per_family
        self.running = False
        self.last_insight_times: Dict[str, datetime] = {}
        
    async def start(self):
        """Start the proactive scheduler."""
        self.running = True
        logger.info(f"Starting proactive scheduler (interval: {self.interval_hours}h)")
        
        while self.running:
            try:
                await self.run_proactive_loop()
                await asyncio.sleep(self.interval_hours * 3600)  # Convert hours to seconds
            except Exception as e:
                logger.error(f"Error in proactive scheduler: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    async def stop(self):
        """Stop the proactive scheduler."""
        self.running = False
        logger.info("Stopping proactive scheduler")
    
    async def run_proactive_loop(self):
        """Run one iteration of the proactive insight loop."""
        logger.info("Starting proactive insight loop")
        
        # Get all active families
        active_families = await self.get_active_families()
        logger.info(f"Found {len(active_families)} active families")
        
        for family in active_families:
            try:
                await self.process_family_insights(family)
            except Exception as e:
                logger.error(f"Error processing family {family.family_id}: {e}")
        
        logger.info("Completed proactive insight loop")
    
    async def get_active_families(self) -> List[Any]:
        """Get all active families."""
        try:
            # Get all families from storage
            all_families = []
            families_data = families._read()
            
            for family_id, family_data in families_data.items():
                if family_id == "legacy_chat_ids":  # Skip legacy data
                    continue
                
                try:
                    family = families.get_family(family_id)
                    if family and family.status == "active":
                        all_families.append(family)
                except Exception as e:
                    logger.warning(f"Error loading family {family_id}: {e}")
            
            return all_families
            
        except Exception as e:
            logger.error(f"Error getting active families: {e}")
            return []
    
    async def process_family_insights(self, family: Any):
        """Process insights for a single family."""
        family_id = family.family_id
        
        # Check if we should send an insight (rate limiting)
        if not self.should_send_insight(family_id):
            logger.debug(f"Skipping family {family_id} - rate limited")
            return
        
        # Get family context
        context = await self.build_family_context(family)
        
        # Generate insight
        insight = await self.generate_insight(family, context)
        
        if insight:
            # Send insight to family members
            await self.send_insight_to_family(family, insight)
            
            # Update last insight time
            self.last_insight_times[family_id] = datetime.now()
            
            logger.info(f"Sent proactive insight to family {family_id}")
    
    def should_send_insight(self, family_id: str) -> bool:
        """Check if we should send an insight to this family (rate limiting)."""
        if family_id not in self.last_insight_times:
            return True
        
        last_time = self.last_insight_times[family_id]
        time_since_last = datetime.now() - last_time
        
        # Only send one insight per 6 hours per family
        return time_since_last >= timedelta(hours=6)
    
    async def build_family_context(self, family: Any) -> Dict[str, Any]:
        """Build context for insight generation."""
        try:
            # Get recent events
            recent_events = storage.get_recent_events(family.family_id, limit=10)
            
            # Get family profile
            family_profile = {
                "family_id": family.family_id,
                "parent_name": family.parent_name,
                "children_count": len(family.children),
                "enabled_dyads": family.enabled_dyads,
                "lifestyle_tags": family.lifestyle_tags,
                "timezone": family.timezone,
                "cloud_reasoning": family.cloud_reasoning
            }
            
            # Get recent insights
            recent_insights = [e for e in recent_events if e.get("event") == "insight"]
            
            context = {
                "family": family_profile,
                "recent_events": recent_events,
                "recent_insights": recent_insights,
                "current_time": datetime.now().isoformat(),
                "timezone": family.timezone
            }
            
            return context
            
        except Exception as e:
            logger.error(f"Error building family context: {e}")
            return {}
    
    async def generate_insight(self, family: Any, context: Dict[str, Any]) -> Optional[str]:
        """Generate an insight for the family."""
        try:
            # Check if reasoning is enabled for this family
            if not family.cloud_reasoning:
                return await self.generate_scripted_insight(family, context)
            
            # Use AI reasoning
            return await self.generate_ai_insight(family, context)
            
        except Exception as e:
            logger.error(f"Error generating insight: {e}")
            return None
    
    async def generate_scripted_insight(self, family: Any, context: Dict[str, Any]) -> str:
        """Generate a scripted insight (no AI)."""
        # Simple scripted insights based on context
        recent_events = context.get("recent_events", [])
        
        # Count different types of events
        dyad_sessions = [e for e in recent_events if "dyad" in e.get("labels", [])]
        voice_notes = [e for e in recent_events if e.get("event") == "voice_analyzed"]
        
        if not recent_events:
            return "💡 **Proactive Insight**\n\nReady to start your parenting journey? Try using one of your enabled Dyads to get personalized insights."
        
        if len(dyad_sessions) == 0:
            return "💡 **Proactive Insight**\n\nI notice you haven't used your Dyads yet. They're designed to provide personalized support for your specific parenting challenges."
        
        if len(voice_notes) > 0:
            return "💡 **Proactive Insight**\n\nGreat job staying engaged! Consider trying a different Dyad to explore new aspects of your parenting journey."
        
        return "💡 **Proactive Insight**\n\nKeep up the great work! Your consistent use of Dyads helps build better patterns for your family."
    
    async def generate_ai_insight(self, family: Any, context: Dict[str, Any]) -> str:
        """Generate an AI-powered insight."""
        try:
            # Prepare context for reasoner
            sanitized_context = self.sanitize_context_for_reasoner(context)
            
            # Create reasoner prompt
            prompt = self.create_insight_prompt(family, sanitized_context)
            
            # Get reasoner response
            reasoner_config = create_reasoner_config()
            response = await get_reasoner_response(
                prompt=prompt,
                context=sanitized_context,
                config=reasoner_config
            )
            
            if response and response.get("tips"):
                # Format the insight
                insight_text = "💡 **AI Insight**\n\n"
                insight_text += response.get("tips", [""])[0]  # Take first tip
                return insight_text
            
            # Fallback to scripted insight
            return await self.generate_scripted_insight(family, context)
            
        except Exception as e:
            logger.error(f"Error generating AI insight: {e}")
            # Fallback to scripted insight
            return await self.generate_scripted_insight(family, context)
    
    def sanitize_context_for_reasoner(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize context for the reasoner (remove PII, etc.)."""
        sanitized = context.copy()
        
        # Remove sensitive information
        if "family" in sanitized:
            family = sanitized["family"].copy()
            family.pop("parent_name", None)
            sanitized["family"] = family
        
        # Limit recent events to avoid context overflow
        if "recent_events" in sanitized:
            sanitized["recent_events"] = sanitized["recent_events"][:5]
        
        return sanitized
    
    def create_insight_prompt(self, family: Any, context: Dict[str, Any]) -> str:
        """Create a prompt for insight generation."""
        return f"""
You are Silli, a supportive parenting AI. Generate a brief, encouraging insight for this family.

Family Context:
- Children: {len(family.children)}
- Enabled Dyads: {', '.join(family.enabled_dyads) if family.enabled_dyads else 'None'}
- Recent activity: {len(context.get('recent_events', []))} events

Generate ONE short, actionable insight (max 2 sentences) that:
1. Acknowledges their parenting journey
2. Suggests a gentle next step
3. Maintains a warm, supportive tone

Focus on their enabled Dyads and recent activity patterns.
"""
    
    async def send_insight_to_family(self, family: Any, insight: str):
        """Send insight to all family members."""
        try:
            # This would typically send via Telegram bot
            # For now, we'll log the insight and store it
            
            # Store the insight event
            event = {
                "ts": datetime.now(),
                "family_id": family.family_id,
                "session_id": f"proactive_insight_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "phase": "proactive",
                "actor": "system",
                "event": "insight",
                "description": insight,
                "labels": ["proactive", "insight"]
            }
            
            storage.append_event(event)
            
            # Log the insight
            logger.info(f"Proactive insight for family {family.family_id}: {insight}")
            
            # TODO: In a real implementation, this would send via Telegram bot
            # await bot.send_message(chat_id=member_id, text=insight)
            
        except Exception as e:
            logger.error(f"Error sending insight to family {family.family_id}: {e}")


# Global scheduler instance
scheduler = ProactiveScheduler()


async def start_scheduler():
    """Start the proactive scheduler."""
    await scheduler.start()


async def stop_scheduler():
    """Stop the proactive scheduler."""
    await scheduler.stop()


def get_scheduler_status() -> Dict[str, Any]:
    """Get scheduler status information."""
    return {
        "running": scheduler.running,
        "interval_hours": scheduler.interval_hours,
        "last_insight_times": {
            family_id: last_time.isoformat() 
            for family_id, last_time in scheduler.last_insight_times.items()
        }
    }
