"""
Unit tests for i18n functionality
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from bot.i18n import get_locale, set_locale, get_supported_locales, is_supported_locale
from bot.profiles import ProfilesStore, FamilyProfile
from datetime import datetime


class TestI18n:
    """Test i18n functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        # Create temporary data directory
        self.temp_dir = tempfile.mkdtemp()
        self.profiles = ProfilesStore(data_dir=self.temp_dir)
        
        # Create a test profile
        self.test_chat_id = 123456789
        self.test_family_id = f"fam_{self.test_chat_id}"
        
        profile = FamilyProfile(
            family_id=self.test_family_id,
            creator_chat_id=self.test_chat_id,
            members=[self.test_chat_id],
            parent_name="Test Parent",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.profiles._index[self.test_family_id] = profile
        self.profiles._save_index()
    
    def teardown_method(self):
        """Cleanup test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_get_supported_locales(self):
        """Test getting supported locales."""
        locales = get_supported_locales()
        assert "en" in locales
        assert "pt_br" in locales
        assert len(locales) == 2
    
    def test_is_supported_locale(self):
        """Test locale validation."""
        assert is_supported_locale("en") == True
        assert is_supported_locale("pt_br") == True
        assert is_supported_locale("fr") == False
        assert is_supported_locale("") == False
    
    def test_get_locale_default(self):
        """Test getting default locale when none is set."""
        with patch('bot.i18n.profiles', self.profiles):
            locale = get_locale(self.test_chat_id)
            assert locale == "en"
    
    def test_get_locale_custom(self):
        """Test getting custom locale."""
        # Set custom locale
        self.profiles.upsert_fields_sync(self.test_chat_id, {"locale": "pt_br"})
        
        with patch('bot.i18n.profiles', self.profiles):
            locale = get_locale(self.test_chat_id)
            assert locale == "pt_br"
    
    def test_get_locale_invalid(self):
        """Test getting invalid locale falls back to default."""
        # Set invalid locale
        self.profiles.upsert_fields_sync(self.test_chat_id, {"locale": "invalid"})
        
        with patch('bot.i18n.profiles', self.profiles):
            locale = get_locale(self.test_chat_id)
            assert locale == "en"
    
    def test_set_locale_valid(self):
        """Test setting valid locale."""
        with patch('bot.i18n.profiles', self.profiles):
            success = set_locale(self.test_chat_id, "pt_br")
            assert success == True
            
            # Verify it was set
            locale = get_locale(self.test_chat_id)
            assert locale == "pt_br"
    
    def test_set_locale_invalid(self):
        """Test setting invalid locale fails."""
        with patch('bot.i18n.profiles', self.profiles):
            success = set_locale(self.test_chat_id, "invalid")
            assert success == False
            
            # Verify default is still used
            locale = get_locale(self.test_chat_id)
            assert locale == "en"
    
    def test_set_locale_nonexistent_user(self):
        """Test setting locale for non-existent user."""
        with patch('bot.i18n.profiles', self.profiles):
            success = set_locale(999999, "pt_br")
            assert success == False
    
    def test_round_trip_locale(self):
        """Test round-trip locale setting and getting."""
        with patch('bot.i18n.profiles', self.profiles):
            # Set to PT-BR
            success = set_locale(self.test_chat_id, "pt_br")
            assert success == True
            
            # Get it back
            locale = get_locale(self.test_chat_id)
            assert locale == "pt_br"
            
            # Change to EN
            success = set_locale(self.test_chat_id, "en")
            assert success == True
            
            # Get it back
            locale = get_locale(self.test_chat_id)
            assert locale == "en"
    
    def test_get_locale_error_handling(self):
        """Test error handling in get_locale."""
        with patch('bot.i18n.profiles') as mock_profiles:
            mock_profiles.get_profile_by_chat_sync.side_effect = Exception("Test error")
            
            locale = get_locale(self.test_chat_id)
            assert locale == "en"  # Should fall back to default
    
    def test_set_locale_error_handling(self):
        """Test error handling in set_locale."""
        with patch('bot.i18n.profiles') as mock_profiles:
            mock_profiles.upsert_fields_sync.side_effect = Exception("Test error")
            
            success = set_locale(self.test_chat_id, "pt_br")
            assert success == False


if __name__ == "__main__":
    pytest.main([__file__])
