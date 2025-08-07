import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from bot.handlers_commands import (
    about_command,
    insights_command,
    reasoning_command,
    familyprofile_command,
    summondyad_command,
    feedback_command,
    more_command,
    handle_dyad_summon
)


class TestCommandHandlers:
    """Test the new command handlers."""
    
    @pytest.mark.asyncio
    async def test_about_command(self):
        """Test the about command."""
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        
        with patch('bot.i18n.get_locale') as mock_get_locale, \
             patch('bot.handlers_onboarding.start_roadshow') as mock_start_roadshow:
            
            mock_get_locale.return_value = "en"
            
            await about_command(mock_message)
            
            mock_start_roadshow.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_insights_command_no_profile(self):
        """Test insights command with no family profile."""
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.answer = AsyncMock()
        
        with patch('bot.i18n.get_locale') as mock_get_locale, \
             patch('bot.profiles.profiles.get_profile_by_chat_sync') as mock_get_profile:
            
            mock_get_locale.return_value = "en"
            mock_get_profile.return_value = None
            
            await insights_command(mock_message)
            
            mock_message.answer.assert_called_once()
            assert "No family profile found" in mock_message.answer.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_reasoning_command_toggle(self):
        """Test reasoning command toggle."""
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.answer = AsyncMock()
        
        mock_profile = {"family_id": "fam_test"}
        mock_family = MagicMock()
        mock_family.cloud_reasoning = False
        
        with patch('bot.i18n.get_locale') as mock_get_locale, \
             patch('bot.profiles.profiles.get_profile_by_chat_sync') as mock_get_profile, \
             patch('bot.families.families.get_family') as mock_get_family, \
             patch('bot.families.families.upsert_fields') as mock_upsert:
            
            mock_get_locale.return_value = "en"
            mock_get_profile.return_value = mock_profile
            mock_get_family.return_value = mock_family
            mock_upsert.return_value = mock_family
            
            await reasoning_command(mock_message)
            
            mock_upsert.assert_called_once_with("fam_test", cloud_reasoning=True)
            mock_message.answer.assert_called_once()
            assert "AI Enabled" in mock_message.answer.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_familyprofile_command(self):
        """Test family profile command."""
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.answer = AsyncMock()
        
        mock_profile = {"family_id": "fam_test"}
        mock_family = MagicMock()
        mock_family.family_id = "fam_test"
        mock_family.parent_name = "Test Parent"
        mock_family.children = [MagicMock()]
        mock_family.members = [12345]
        mock_family.enabled_dyads = ["night_helper"]
        mock_family.cloud_reasoning = True
        
        with patch('bot.i18n.get_locale') as mock_get_locale, \
             patch('bot.profiles.profiles.get_profile_by_chat_sync') as mock_get_profile, \
             patch('bot.families.families.get_family') as mock_get_family:
            
            mock_get_locale.return_value = "en"
            mock_get_profile.return_value = mock_profile
            mock_get_family.return_value = mock_family
            
            await familyprofile_command(mock_message)
            
            mock_message.answer.assert_called_once()
            assert "Family Profile" in mock_message.answer.call_args[0][0]
            assert "Test Parent" in mock_message.answer.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_summondyad_command_no_dyads(self):
        """Test summondyad command with no enabled dyads."""
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.answer = AsyncMock()
        
        mock_profile = {"family_id": "fam_test"}
        mock_family = MagicMock()
        mock_family.enabled_dyads = []
        
        with patch('bot.i18n.get_locale') as mock_get_locale, \
             patch('bot.profiles.profiles.get_profile_by_chat_sync') as mock_get_profile, \
             patch('bot.families.families.get_family') as mock_get_family:
            
            mock_get_locale.return_value = "en"
            mock_get_profile.return_value = mock_profile
            mock_get_family.return_value = mock_family
            
            await summondyad_command(mock_message)
            
            mock_message.answer.assert_called_once()
            assert "No Dyads enabled" in mock_message.answer.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_feedback_command_with_text(self):
        """Test feedback command with text."""
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.text = "/feedback This is great!"
        mock_message.from_user.first_name = "Test"
        mock_message.from_user.last_name = "User"
        mock_message.from_user.username = "testuser"
        mock_message.answer = AsyncMock()
        
        with patch('bot.i18n.get_locale') as mock_get_locale, \
             patch('builtins.open', create=True) as mock_open, \
             patch('pathlib.Path') as mock_path:
            
            mock_get_locale.return_value = "en"
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            await feedback_command(mock_message)
            
            mock_file.write.assert_called_once()
            mock_message.answer.assert_called_once()
            assert "Feedback Sent" in mock_message.answer.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_more_command(self):
        """Test more command."""
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.answer = AsyncMock()
        
        with patch('bot.i18n.get_locale') as mock_get_locale:
            mock_get_locale.return_value = "en"
            
            await more_command(mock_message)
            
            mock_message.answer.assert_called_once()
            assert "Legacy Commands" in mock_message.answer.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_handle_dyad_summon(self):
        """Test Dyad summon callback."""
        mock_callback = MagicMock()
        mock_callback.data = "dyad:summon:night_helper"
        mock_callback.message.chat.id = 12345
        mock_callback.message.edit_text = AsyncMock()
        
        mock_profile = {"family_id": "fam_test"}
        mock_dyad_info = {"name": "Night Helper"}
        
        with patch('bot.i18n.get_locale') as mock_get_locale, \
             patch('bot.profiles.profiles.get_profile_by_chat_sync') as mock_get_profile, \
             patch('bot.dyad_registry.dyad_registry.create_dyad_url') as mock_create_url, \
             patch('bot.dyad_registry.dyad_registry.get_dyad') as mock_get_dyad:
            
            mock_get_locale.return_value = "en"
            mock_get_profile.return_value = mock_profile
            mock_create_url.return_value = "https://example.com"
            mock_get_dyad.return_value = mock_dyad_info
            
            await handle_dyad_summon(mock_callback)
            
            mock_callback.answer.assert_called_once()
            mock_callback.message.edit_text.assert_called_once()
            assert "Night Helper" in mock_callback.message.edit_text.call_args[0][0]


class TestDyadConsent:
    """Test Dyad consent functionality."""
    
    @pytest.mark.asyncio
    async def test_dyad_consent_yes(self):
        """Test accepting Dyad consent."""
        from bot.handlers_family_create import handle_dyad_consent
        
        mock_callback = MagicMock()
        mock_callback.data = "dyad:consent:yes:night_helper"
        mock_callback.message.chat.id = 12345
        mock_callback.message.edit_text = AsyncMock()
        
        mock_profile = {"family_id": "fam_test"}
        mock_family = MagicMock()
        mock_family.enabled_dyads = []
        mock_dyad_info = {"name": "Night Helper"}
        
        with patch('bot.i18n.get_locale') as mock_get_locale, \
             patch('bot.profiles.profiles.get_profile_by_chat_sync') as mock_get_profile, \
             patch('bot.families.families.get_family') as mock_get_family, \
             patch('bot.families.families.upsert_fields') as mock_upsert, \
             patch('bot.dyad_registry.dyad_registry.get_dyad') as mock_get_dyad, \
             patch('asyncio.sleep') as mock_sleep, \
             patch('bot.handlers_family_create.show_dyad_selection') as mock_show:
            
            mock_get_locale.return_value = "en"
            mock_get_profile.return_value = mock_profile
            mock_get_family.return_value = mock_family
            mock_upsert.return_value = mock_family
            mock_get_dyad.return_value = mock_dyad_info
            
            await handle_dyad_consent(mock_callback)
            
            mock_upsert.assert_called_once_with("fam_test", enabled_dyads=["night_helper"])
            mock_callback.message.edit_text.assert_called()
            assert "Enabled" in mock_callback.message.edit_text.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_dyad_consent_no(self):
        """Test declining Dyad consent."""
        from bot.handlers_family_create import handle_dyad_consent
        
        mock_callback = MagicMock()
        mock_callback.data = "dyad:consent:no:night_helper"
        mock_callback.message.chat.id = 12345
        
        with patch('bot.handlers_family_create.show_dyad_selection') as mock_show:
            
            await handle_dyad_consent(mock_callback)
            
            mock_show.assert_called_once_with(mock_callback.message)


class TestDyadRegistryConsent:
    """Test Dyad registry consent text functionality."""
    
    def test_get_dyad_consent_text(self):
        """Test getting consent text from Dyad registry."""
        from bot.dyad_registry import DyadRegistry
        
        # Create a mock registry with consent text
        registry_data = {
            "dyads": {
                "night_helper": {
                    "consent_text": {
                        "en": "English consent text",
                        "pt_br": "Portuguese consent text"
                    }
                }
            }
        }
        
        with patch('builtins.open', create=True) as mock_open, \
             patch('yaml.safe_load') as mock_yaml_load:
            
            mock_yaml_load.return_value = registry_data
            registry = DyadRegistry("test.yaml")
            
            # Test English consent text
            consent_en = registry.get_dyad_consent_text("night_helper", "en")
            assert consent_en == "English consent text"
            
            # Test Portuguese consent text
            consent_pt = registry.get_dyad_consent_text("night_helper", "pt_br")
            assert consent_pt == "Portuguese consent text"
            
            # Test fallback to English
            consent_fallback = registry.get_dyad_consent_text("night_helper", "fr")
            assert consent_fallback == "English consent text"
    
    def test_get_dyad_consent_text_missing_dyad(self):
        """Test getting consent text for missing Dyad."""
        from bot.dyad_registry import DyadRegistry
        
        registry_data = {"dyads": {}}
        
        with patch('builtins.open', create=True) as mock_open, \
             patch('yaml.safe_load') as mock_yaml_load:
            
            mock_yaml_load.return_value = registry_data
            registry = DyadRegistry("test.yaml")
            
            consent = registry.get_dyad_consent_text("missing_dyad", "en")
            assert "Unknown Dyad" in consent
