"""
Summary card rendering for Wind-Down analysis results.
Creates PNG images with score, badges, tips, and timestamp.
"""

import os
from datetime import datetime
from typing import List
from PIL import Image, ImageDraw, ImageFont
from loguru import logger


def render_summary_card(score: int, badges: List[str], tips: List[str], output_path: str):
    """Render a summary card as PNG image."""
    try:
        # Card dimensions
        width, height = 800, 600
        
        # Create image with gradient background
        image = Image.new('RGB', (width, height), color='#1a1a2e')
        draw = ImageDraw.Draw(image)
        
        # Try to load fonts, fall back to default if not available
        try:
            title_font = ImageFont.truetype("Arial.ttf", 32)
            subtitle_font = ImageFont.truetype("Arial.ttf", 20)
            body_font = ImageFont.truetype("Arial.ttf", 16)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
        
        # Header
        draw.text((width//2, 50), "Wind-Down Analysis", 
                 fill='#ffffff', font=title_font, anchor="mm")
        
        # Score circle
        score_x, score_y = width//2, 150
        score_radius = 80
        
        # Score color based on value
        if score >= 80:
            score_color = '#4ade80'  # Green
        elif score >= 60:
            score_color = '#fbbf24'  # Yellow
        else:
            score_color = '#f87171'  # Red
        
        # Draw score circle
        draw.ellipse([score_x - score_radius, score_y - score_radius,
                     score_x + score_radius, score_y + score_radius],
                    outline=score_color, width=4)
        
        # Score text
        draw.text((score_x, score_y), f"{score}", 
                 fill=score_color, font=title_font, anchor="mm")
        draw.text((score_x, score_y + 40), "Score", 
                 fill='#ffffff', font=subtitle_font, anchor="mm")
        
        # Badges section
        badge_y = 280
        draw.text((50, badge_y), "Detected Features:", 
                 fill='#ffffff', font=subtitle_font)
        
        badge_colors = {
            "Speech present": "#3b82f6",
            "Music/TV present": "#8b5cf6", 
            "Fluctuating": "#f59e0b",
            "Steady": "#10b981"
        }
        
        badge_x = 50
        for i, badge in enumerate(badges):
            color = badge_colors.get(badge, "#6b7280")
            draw.rectangle([badge_x, badge_y + 30 + i*30, 
                          badge_x + 200, badge_y + 55 + i*30],
                         fill=color, outline='#ffffff', width=1)
            draw.text((badge_x + 10, badge_y + 42 + i*30), badge,
                     fill='#ffffff', font=body_font)
            badge_x += 220
            if badge_x > width - 200:
                badge_x = 50
                badge_y += 60
        
        # Tips section
        tips_y = badge_y + 80
        draw.text((50, tips_y), "Suggestions:", 
                 fill='#ffffff', font=subtitle_font)
        
        for i, tip in enumerate(tips):
            # Wrap text to fit width
            words = tip.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + " " + word if current_line else word
                bbox = draw.textbbox((0, 0), test_line, font=body_font)
                if bbox[2] > width - 100:
                    lines.append(current_line)
                    current_line = word
                else:
                    current_line = test_line
            
            if current_line:
                lines.append(current_line)
            
            # Draw tip lines
            for j, line in enumerate(lines):
                draw.text((50, tips_y + 30 + i*50 + j*20), f"• {line}",
                         fill='#e5e7eb', font=body_font)
        
        # Footer with timestamp and Silli mark
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        draw.text((width//2, height - 60), timestamp,
                 fill='#9ca3af', font=body_font, anchor="mm")
        
        # Small Silli mark
        draw.text((width - 50, height - 30), "Silli",
                 fill='#10b981', font=body_font, anchor="mm")
        
        # Save image
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        image.save(output_path, 'PNG')
        
        logger.info(f"Rendered summary card to {output_path}")
        
    except Exception as e:
        logger.error(f"Error rendering summary card: {e}")
        raise


def create_sample_card():
    """Create a sample card for testing."""
    sample_score = 75
    sample_badges = ["Steady", "Speech present"]
    sample_tips = [
        "Dim lights to warm (~1800K); hide bright screens.",
        "Lullaby pacing ~60–70 BPM; mirror child, then fade."
    ]
    
    output_path = "data/sample_card.png"
    render_summary_card(sample_score, sample_badges, sample_tips, output_path)
    logger.info(f"Created sample card at {output_path}") 