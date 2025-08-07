import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from bot.families import FamiliesStore
from bot.profiles import FamilyProfile, Child


class TestFamiliesStore:
    """Test the FamiliesStore functionality."""
    
    @pytest.fixture
    def families_store(self, tmp_path):
        """Create a FamiliesStore instance with temporary path."""
        families_file = tmp_path / "families.json"
        return FamiliesStore(str(families_file))
    
    @pytest.fixture
    def sample_family_data(self):
        """Sample family data for testing."""
        return {
            "family_id": "fam_12345_20250101_120000",
            "creator_chat_id": 12345,
            "members": [12345],
            "parent_name": "Test Parent",
            "children": [{
                "name": "Test Child",
                "sex": "m",
                "age_years": 5.0,
                "health_notes": "None"
            }],
            "lifestyle_tags": ["sports", "music"],
            "enabled_dyads": ["night_helper"],
            "status": "active",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
    
    def test_save_and_get_family(self, families_store, sample_family_data):
        """Test saving and retrieving a family profile."""
        # Save family
        families_store.save_family(sample_family_data)
        
        # Retrieve family
        family = families_store.get_family(sample_family_data["family_id"])
        
        assert family is not None
        assert family.family_id == sample_family_data["family_id"]
        assert family.parent_name == sample_family_data["parent_name"]
        assert len(family.children) == 1
        assert family.children[0].name == "Test Child"
    
    def test_upsert_fields(self, families_store, sample_family_data):
        """Test updating family fields."""
        # Save family
        families_store.save_family(sample_family_data)
        
        # Update fields
        updated_family = families_store.upsert_fields(
            sample_family_data["family_id"],
            parent_name="Updated Parent",
            enabled_dyads=["night_helper", "meal_mood"]
        )
        
        assert updated_family is not None
        assert updated_family.parent_name == "Updated Parent"
        assert "meal_mood" in updated_family.enabled_dyads
    
    def test_add_and_remove_member(self, families_store, sample_family_data):
        """Test adding and removing family members."""
        # Save family
        families_store.save_family(sample_family_data)
        
        # Add member
        family = families_store.add_member(sample_family_data["family_id"], 67890)
        assert family is not None
        assert 67890 in family.members
        
        # Remove member
        family = families_store.remove_member(sample_family_data["family_id"], 67890)
        assert family is not None
        assert 67890 not in family.members
    
    def test_list_members(self, families_store, sample_family_data):
        """Test listing family members."""
        # Save family
        families_store.save_family(sample_family_data)
        
        # Add another member
        families_store.add_member(sample_family_data["family_id"], 67890)
        
        # List members
        members = families_store.list_members(sample_family_data["family_id"])
        assert 12345 in members
        assert 67890 in members
        assert len(members) == 2
    
    def test_generate_join_code(self, families_store, sample_family_data):
        """Test generating join codes."""
        # Save family
        families_store.save_family(sample_family_data)
        
        # Generate join code
        code = families_store.generate_join_code(sample_family_data["family_id"])
        
        assert len(code) == 6
        assert code.isalnum()
        assert code.isupper()
    
    def test_consume_valid_join_code(self, families_store, sample_family_data):
        """Test consuming a valid join code."""
        # Save family
        families_store.save_family(sample_family_data)
        
        # Generate join code
        code = families_store.generate_join_code(sample_family_data["family_id"])
        
        # Consume join code
        family = families_store.consume_join_code(code, 67890)
        
        assert family is not None
        assert 67890 in family.members
    
    def test_consume_invalid_join_code(self, families_store):
        """Test consuming an invalid join code."""
        family = families_store.consume_join_code("INVALID", 67890)
        assert family is None
    
    def test_consume_expired_join_code(self, families_store, sample_family_data):
        """Test consuming an expired join code."""
        # Save family
        families_store.save_family(sample_family_data)
        
        # Generate join code
        code = families_store.generate_join_code(sample_family_data["family_id"])
        
        # Manually expire the code by modifying the data
        data = families_store._read()
        data[sample_family_data["family_id"]]["join_codes"][code]["expires_at"] = (
            datetime.now() - timedelta(hours=1)
        ).isoformat()
        families_store._write(data)
        
        # Try to consume expired code
        family = families_store.consume_join_code(code, 67890)
        assert family is None
    
    def test_consume_used_join_code(self, families_store, sample_family_data):
        """Test consuming an already used join code."""
        # Save family
        families_store.save_family(sample_family_data)
        
        # Generate join code
        code = families_store.generate_join_code(sample_family_data["family_id"])
        
        # Use the code once
        family1 = families_store.consume_join_code(code, 67890)
        assert family1 is not None
        
        # Try to use the same code again
        family2 = families_store.consume_join_code(code, 99999)
        assert family2 is None
    
    def test_cleanup_expired_codes(self, families_store, sample_family_data):
        """Test cleaning up expired join codes."""
        # Save family
        families_store.save_family(sample_family_data)
        
        # Generate multiple codes
        code1 = families_store.generate_join_code(sample_family_data["family_id"])
        code2 = families_store.generate_join_code(sample_family_data["family_id"])
        
        # Manually expire one code
        data = families_store._read()
        data[sample_family_data["family_id"]]["join_codes"][code1]["expires_at"] = (
            datetime.now() - timedelta(hours=1)
        ).isoformat()
        families_store._write(data)
        
        # Clean up expired codes
        families_store.cleanup_expired_codes()
        
        # Check that expired code is removed
        data = families_store._read()
        assert code1 not in data[sample_family_data["family_id"]]["join_codes"]
        assert code2 in data[sample_family_data["family_id"]]["join_codes"]


class TestFamilyLinkHandlers:
    """Test the family linking handlers."""
    
    @pytest.mark.asyncio
    async def test_handle_family_link_start(self):
        """Test starting the family linking process."""
        from bot.handlers_family_link import handle_family_link_start
        
        mock_callback = MagicMock()
        mock_callback.message.chat.id = 12345
        mock_callback.message.edit_text = AsyncMock()
        mock_state = MagicMock()
        mock_state.set_state = AsyncMock()
        
        with patch('bot.i18n.get_locale') as mock_get_locale:
            mock_get_locale.return_value = "en"
            
            await handle_family_link_start(mock_callback, mock_state)
            
            mock_callback.answer.assert_called_once()
            mock_state.set_state.assert_called_once()
            mock_callback.message.edit_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_join_code_input_success(self):
        """Test successful join code input."""
        from bot.handlers_family_link import handle_join_code_input
        
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.text = "ABC123"
        mock_message.answer = AsyncMock()
        mock_state = MagicMock()
        mock_state.clear = AsyncMock()
        
        mock_family = MagicMock()
        mock_family.family_id = "fam_test"
        
        with patch('bot.i18n.get_locale') as mock_get_locale, \
             patch('bot.families.families.consume_join_code') as mock_consume, \
             patch('bot.profiles.profiles.upsert_fields_sync') as mock_upsert:
            
            mock_get_locale.return_value = "en"
            mock_consume.return_value = mock_family
            
            await handle_join_code_input(mock_message, mock_state)
            
            mock_consume.assert_called_once_with("ABC123", 12345)
            mock_upsert.assert_called_once()
            mock_state.clear.assert_called_once()
            mock_message.answer.assert_called()
    
    @pytest.mark.asyncio
    async def test_handle_join_code_input_invalid(self):
        """Test invalid join code input."""
        from bot.handlers_family_link import handle_join_code_input
        
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.text = "INVALID"
        mock_message.answer = AsyncMock()
        mock_state = MagicMock()
        mock_state.clear = AsyncMock()
        
        with patch('bot.i18n.get_locale') as mock_get_locale, \
             patch('bot.families.families.consume_join_code') as mock_consume:
            
            mock_get_locale.return_value = "en"
            mock_consume.return_value = None
            
            await handle_join_code_input(mock_message, mock_state)
            
            mock_consume.assert_called_once_with("INVALID", 12345)
            mock_state.clear.assert_not_called()
            mock_message.answer.assert_called()


class TestFamilyCreateHandlers:
    """Test the family creation handlers."""
    
    @pytest.mark.asyncio
    async def test_handle_dyad_toggle(self):
        """Test toggling dyads."""
        from bot.handlers_family_create import handle_dyad_toggle
        
        mock_callback = MagicMock()
        mock_callback.data = "dyad:night_helper"
        mock_callback.message.chat.id = 12345
        mock_callback.answer = AsyncMock()
        
        mock_family = MagicMock()
        mock_family.enabled_dyads = []
        
        with patch('bot.profiles.profiles.get_profile_by_chat_sync') as mock_get_profile, \
             patch('bot.families.families.get_family') as mock_get_family, \
             patch('bot.families.families.upsert_fields') as mock_upsert, \
             patch('bot.i18n.get_locale') as mock_get_locale:
            
            mock_get_profile.return_value = {"family_id": "fam_test"}
            mock_get_family.return_value = mock_family
            mock_upsert.return_value = mock_family
            mock_get_locale.return_value = "en"
            
            await handle_dyad_toggle(mock_callback)
            
            mock_upsert.assert_called_once_with("fam_test", enabled_dyads=["night_helper"])
            mock_callback.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_generate_join_code(self):
        """Test generating join codes."""
        from bot.handlers_family_create import handle_generate_join_code
        
        mock_callback = MagicMock()
        mock_callback.message.chat.id = 12345
        mock_callback.message.edit_text = AsyncMock()
        
        with patch('bot.profiles.profiles.get_profile_by_chat_sync') as mock_get_profile, \
             patch('bot.families.families.generate_join_code') as mock_generate, \
             patch('bot.i18n.get_locale') as mock_get_locale:
            
            mock_get_profile.return_value = {"family_id": "fam_test"}
            mock_generate.return_value = "ABC123"
            mock_get_locale.return_value = "en"
            
            await handle_generate_join_code(mock_callback)
            
            mock_generate.assert_called_once_with("fam_test")
            mock_callback.message.edit_text.assert_called_once()
            assert "ABC123" in mock_callback.message.edit_text.call_args[0][0]
