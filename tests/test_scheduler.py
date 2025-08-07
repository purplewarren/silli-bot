import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from bot.scheduler import ProactiveScheduler


class TestProactiveScheduler:
    """Test the ProactiveScheduler functionality."""
    
    @pytest.fixture
    def scheduler(self):
        """Create a ProactiveScheduler instance for testing."""
        return ProactiveScheduler(interval_hours=1, max_insights_per_family=1)
    
    @pytest.fixture
    def mock_family(self):
        """Create a mock family for testing."""
        family = MagicMock()
        family.family_id = "fam_test"
        family.parent_name = "Test Parent"
        family.children = [MagicMock()]
        family.enabled_dyads = ["night_helper"]
        family.lifestyle_tags = ["sports"]
        family.timezone = "UTC"
        family.cloud_reasoning = True
        family.status = "active"
        return family
    
    def test_scheduler_initialization(self, scheduler):
        """Test scheduler initialization."""
        assert scheduler.interval_hours == 1
        assert scheduler.max_insights_per_family == 1
        assert scheduler.running == False
        assert scheduler.last_insight_times == {}
    
    def test_should_send_insight_new_family(self, scheduler):
        """Test should_send_insight for new family."""
        assert scheduler.should_send_insight("new_family") == True
    
    def test_should_send_insight_rate_limited(self, scheduler):
        """Test should_send_insight for rate limited family."""
        family_id = "test_family"
        scheduler.last_insight_times[family_id] = datetime.now()
        
        # Should not send if less than 6 hours have passed
        assert scheduler.should_send_insight(family_id) == False
    
    def test_should_send_insight_after_rate_limit(self, scheduler):
        """Test should_send_insight after rate limit expires."""
        family_id = "test_family"
        scheduler.last_insight_times[family_id] = datetime.now() - timedelta(hours=7)
        
        # Should send if more than 6 hours have passed
        assert scheduler.should_send_insight(family_id) == True
    
    @pytest.mark.asyncio
    async def test_build_family_context(self, scheduler, mock_family):
        """Test building family context."""
        with patch('bot.storage.storage.get_recent_events') as mock_get_events:
            mock_get_events.return_value = [
                {"event": "insight", "description": "Test insight"},
                {"event": "dyad_launched", "labels": ["night_helper"]}
            ]
            
            context = await scheduler.build_family_context(mock_family)
            
            assert context["family"]["family_id"] == "fam_test"
            assert context["family"]["parent_name"] == "Test Parent"
            assert context["family"]["children_count"] == 1
            assert context["family"]["enabled_dyads"] == ["night_helper"]
            assert context["family"]["cloud_reasoning"] == True
            assert len(context["recent_events"]) == 2
            assert len(context["recent_insights"]) == 1
    
    @pytest.mark.asyncio
    async def test_generate_scripted_insight_no_events(self, scheduler, mock_family):
        """Test generating scripted insight with no events."""
        context = {"recent_events": []}
        
        insight = await scheduler.generate_scripted_insight(mock_family, context)
        
        assert "Ready to start your parenting journey" in insight
        assert "Proactive Insight" in insight
    
    @pytest.mark.asyncio
    async def test_generate_scripted_insight_with_dyad_sessions(self, scheduler, mock_family):
        """Test generating scripted insight with dyad sessions."""
        context = {
            "recent_events": [
                {"event": "dyad_launched", "labels": ["night_helper"]},
                {"event": "voice_analyzed"}
            ]
        }
        
        insight = await scheduler.generate_scripted_insight(mock_family, context)
        
        assert "Great job staying engaged" in insight
        assert "Proactive Insight" in insight
    
    @pytest.mark.asyncio
    async def test_generate_scripted_insight_with_voice_notes(self, scheduler, mock_family):
        """Test generating scripted insight with voice notes."""
        context = {
            "recent_events": [
                {"event": "voice_analyzed"},
                {"event": "voice_analyzed"}
            ]
        }
        
        insight = await scheduler.generate_scripted_insight(mock_family, context)
        
        assert "Great job staying engaged" in insight
        assert "Proactive Insight" in insight
    
    @pytest.mark.asyncio
    async def test_generate_ai_insight_success(self, scheduler, mock_family):
        """Test generating AI insight successfully."""
        context = {
            "recent_events": [
                {"event": "dyad_launched", "labels": ["night_helper"]}
            ]
        }
        
        mock_response = {"tips": ["Try using the Night Helper more often for better sleep patterns."]}
        
        with patch('bot.reason_client.get_reasoner_response') as mock_reasoner:
            mock_reasoner.return_value = mock_response
            
            insight = await scheduler.generate_ai_insight(mock_family, context)
            
            assert "AI Insight" in insight
            assert "Try using the Night Helper" in insight
    
    @pytest.mark.asyncio
    async def test_generate_ai_insight_fallback(self, scheduler, mock_family):
        """Test AI insight generation falls back to scripted."""
        context = {"recent_events": []}
        
        with patch('bot.reason_client.get_reasoner_response') as mock_reasoner:
            mock_reasoner.side_effect = Exception("Reasoner error")
            
            insight = await scheduler.generate_ai_insight(mock_family, context)
            
            assert "Proactive Insight" in insight
            assert "Ready to start your parenting journey" in insight
    
    @pytest.mark.asyncio
    async def test_generate_insight_ai_enabled(self, scheduler, mock_family):
        """Test insight generation with AI enabled."""
        context = {"recent_events": []}
        
        with patch.object(scheduler, 'generate_ai_insight') as mock_ai_insight:
            mock_ai_insight.return_value = "AI insight"
            
            insight = await scheduler.generate_insight(mock_family, context)
            
            mock_ai_insight.assert_called_once_with(mock_family, context)
            assert insight == "AI insight"
    
    @pytest.mark.asyncio
    async def test_generate_insight_ai_disabled(self, scheduler, mock_family):
        """Test insight generation with AI disabled."""
        mock_family.cloud_reasoning = False
        context = {"recent_events": []}
        
        with patch.object(scheduler, 'generate_scripted_insight') as mock_scripted:
            mock_scripted.return_value = "Scripted insight"
            
            insight = await scheduler.generate_insight(mock_family, context)
            
            mock_scripted.assert_called_once_with(mock_family, context)
            assert insight == "Scripted insight"
    
    def test_sanitize_context_for_reasoner(self, scheduler):
        """Test context sanitization for reasoner."""
        context = {
            "family": {
                "family_id": "fam_test",
                "parent_name": "John Doe",  # Should be removed
                "children_count": 2
            },
            "recent_events": [{"event": "test"} for _ in range(10)]  # Should be limited
        }
        
        sanitized = scheduler.sanitize_context_for_reasoner(context)
        
        assert "parent_name" not in sanitized["family"]
        assert len(sanitized["recent_events"]) == 5  # Limited to 5
    
    def test_create_insight_prompt(self, scheduler, mock_family):
        """Test creating insight prompt."""
        context = {"recent_events": [{"event": "test"}]}
        
        prompt = scheduler.create_insight_prompt(mock_family, context)
        
        assert "Silli" in prompt
        assert "parenting AI" in prompt
        assert "night_helper" in prompt
        assert "1 events" in prompt
    
    @pytest.mark.asyncio
    async def test_send_insight_to_family(self, scheduler, mock_family):
        """Test sending insight to family."""
        insight = "Test insight message"
        
        with patch('bot.storage.storage.append_event') as mock_append:
            await scheduler.send_insight_to_family(mock_family, insight)
            
            mock_append.assert_called_once()
            call_args = mock_append.call_args[0][0]
            assert call_args["family_id"] == "fam_test"
            assert call_args["event"] == "insight"
            assert call_args["description"] == insight
            assert "proactive" in call_args["labels"]


class TestSchedulerIntegration:
    """Test scheduler integration with other components."""
    
    @pytest.mark.asyncio
    async def test_get_active_families(self):
        """Test getting active families."""
        scheduler = ProactiveScheduler()
        
        # Mock families data
        mock_families_data = {
            "fam_1": {
                "family_id": "fam_1",
                "status": "active",
                "parent_name": "Parent 1"
            },
            "fam_2": {
                "family_id": "fam_2",
                "status": "inactive",
                "parent_name": "Parent 2"
            },
            "legacy_chat_ids": [123, 456]  # Should be skipped
        }
        
        with patch.object(scheduler, '_read_families_data') as mock_read, \
             patch('bot.families.families.get_family') as mock_get_family:
            
            mock_read.return_value = mock_families_data
            
            # Mock family objects
            active_family = MagicMock()
            active_family.status = "active"
            inactive_family = MagicMock()
            inactive_family.status = "inactive"
            
            mock_get_family.side_effect = lambda fid: active_family if fid == "fam_1" else inactive_family
            
            families = await scheduler.get_active_families()
            
            assert len(families) == 1
            assert families[0].status == "active"
    
    @pytest.mark.asyncio
    async def test_process_family_insights_rate_limited(self):
        """Test processing family insights with rate limiting."""
        scheduler = ProactiveScheduler()
        mock_family = MagicMock()
        mock_family.family_id = "fam_test"
        
        # Set recent insight time
        scheduler.last_insight_times["fam_test"] = datetime.now()
        
        with patch.object(scheduler, 'build_family_context') as mock_build, \
             patch.object(scheduler, 'generate_insight') as mock_generate, \
             patch.object(scheduler, 'send_insight_to_family') as mock_send:
            
            await scheduler.process_family_insights(mock_family)
            
            # Should not process due to rate limiting
            mock_build.assert_not_called()
            mock_generate.assert_not_called()
            mock_send.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_family_insights_success(self):
        """Test successful processing of family insights."""
        scheduler = ProactiveScheduler()
        mock_family = MagicMock()
        mock_family.family_id = "fam_test"
        
        # No recent insight time
        if "fam_test" in scheduler.last_insight_times:
            del scheduler.last_insight_times["fam_test"]
        
        mock_context = {"recent_events": []}
        mock_insight = "Test insight"
        
        with patch.object(scheduler, 'build_family_context') as mock_build, \
             patch.object(scheduler, 'generate_insight') as mock_generate, \
             patch.object(scheduler, 'send_insight_to_family') as mock_send:
            
            mock_build.return_value = mock_context
            mock_generate.return_value = mock_insight
            
            await scheduler.process_family_insights(mock_family)
            
            mock_build.assert_called_once_with(mock_family)
            mock_generate.assert_called_once_with(mock_family, mock_context)
            mock_send.assert_called_once_with(mock_family, mock_insight)
            
            # Should update last insight time
            assert "fam_test" in scheduler.last_insight_times


class TestSchedulerCommands:
    """Test scheduler-related commands."""
    
    @pytest.mark.asyncio
    async def test_scheduler_command(self):
        """Test the /scheduler command."""
        from bot.handlers_commands import scheduler_command
        
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.answer = AsyncMock()
        
        mock_status = {
            "running": True,
            "interval_hours": 3,
            "last_insight_times": {
                "fam_1": "2025-01-01T12:00:00",
                "fam_2": "2025-01-01T13:00:00"
            }
        }
        
        with patch('bot.i18n.get_locale') as mock_get_locale, \
             patch('bot.scheduler.get_scheduler_status') as mock_get_status:
            
            mock_get_locale.return_value = "en"
            mock_get_status.return_value = mock_status
            
            await scheduler_command(mock_message)
            
            mock_message.answer.assert_called_once()
            response_text = mock_message.answer.call_args[0][0]
            assert "Proactive Scheduler Status" in response_text
            assert "Active" in response_text
            assert "3 hours" in response_text
            assert "2 families" in response_text.lower()
    
    @pytest.mark.asyncio
    async def test_scheduler_start_callback(self):
        """Test scheduler start callback."""
        from bot.handlers_commands import handle_scheduler_controls
        
        mock_callback = MagicMock()
        mock_callback.data = "scheduler:start"
        mock_callback.message.chat.id = 12345
        mock_callback.message.edit_text = AsyncMock()
        mock_callback.answer = AsyncMock()
        
        mock_scheduler = MagicMock()
        mock_scheduler.running = False
        
        with patch('bot.i18n.get_locale') as mock_get_locale, \
             patch('bot.scheduler.scheduler', mock_scheduler), \
             patch('asyncio.create_task') as mock_create_task:
            
            mock_get_locale.return_value = "en"
            
            await handle_scheduler_controls(mock_callback)
            
            mock_callback.answer.assert_called_once()
            mock_callback.message.edit_text.assert_called_once()
            assert "started successfully" in mock_callback.message.edit_text.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_scheduler_test_callback(self):
        """Test scheduler test callback."""
        from bot.handlers_commands import handle_scheduler_controls
        
        mock_callback = MagicMock()
        mock_callback.data = "scheduler:test"
        mock_callback.message.chat.id = 12345
        mock_callback.message.edit_text = AsyncMock()
        mock_callback.answer = AsyncMock()
        
        mock_profile = {"family_id": "fam_test"}
        mock_family = MagicMock()
        mock_family.family_id = "fam_test"
        
        with patch('bot.i18n.get_locale') as mock_get_locale, \
             patch('bot.profiles.profiles.get_profile_by_chat_sync') as mock_get_profile, \
             patch('bot.families.families.get_family') as mock_get_family, \
             patch('bot.scheduler.ProactiveScheduler') as mock_scheduler_class:
            
            mock_get_locale.return_value = "en"
            mock_get_profile.return_value = mock_profile
            mock_get_family.return_value = mock_family
            
            mock_scheduler = MagicMock()
            mock_scheduler.build_family_context.return_value = {"recent_events": []}
            mock_scheduler.generate_insight.return_value = "Test insight"
            mock_scheduler_class.return_value = mock_scheduler
            
            await handle_scheduler_controls(mock_callback)
            
            mock_callback.answer.assert_called_once()
            mock_callback.message.edit_text.assert_called_once()
            assert "Test Insight" in mock_callback.message.edit_text.call_args[0][0]
