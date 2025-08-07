import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, CallbackQuery, Chat, User
from bot.gate_middleware import GateMiddleware
from bot.profiles import profiles


class TestGateMiddleware:
    """Test the GateMiddleware functionality."""
    
    @pytest.fixture
    def middleware(self):
        return GateMiddleware()
    
    @pytest.fixture
    def mock_message(self):
        """Create a mock message."""
        message = MagicMock()
        message.chat = MagicMock()
        message.chat.id = 12345
        message.text = "Hello"
        return message
    
    @pytest.fixture
    def mock_callback(self):
        """Create a mock callback query."""
        callback = MagicMock()
        callback.chat = MagicMock()
        callback.chat.id = 12345
        callback.data = "gate:about"
        return callback
    
    @pytest.fixture
    def mock_handler(self):
        """Create a mock handler."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_data(self):
        """Create mock data dict."""
        return {"key": "value"}
    
    @pytest.mark.asyncio
    async def test_callback_queries_bypass_middleware(self, middleware, mock_callback, mock_handler, mock_data):
        """Test that callback queries bypass the middleware."""
        with patch('bot.handlers_gate.show_greeting_card') as mock_show:
            result = await middleware(mock_handler, mock_callback, mock_data)
            
            # Should call the handler directly
            mock_handler.assert_called_once_with(mock_callback, mock_data)
            mock_show.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_unlinked_profile_shows_greeting(self, middleware, mock_message, mock_handler, mock_data):
        """Test that unlinked profiles show greeting card."""
        # Mock the answer method
        mock_message.answer = AsyncMock()
        
        with patch('bot.profiles.profiles.get_profile_by_chat_sync') as mock_get_profile, \
             patch('bot.profiles.profiles.upsert_fields_sync') as mock_upsert, \
             patch('bot.i18n.get_locale') as mock_get_locale:
            
            # Mock no existing profile, then unlinked profile after creation
            mock_get_profile.side_effect = [None, {"status": "unlinked"}]
            mock_get_locale.return_value = "en"
            
            result = await middleware(mock_handler, mock_message, mock_data)
            
            # Should create profile with unlinked status
            mock_upsert.assert_called_once_with(12345, {
                "status": "unlinked",
                "locale": "en"
            })
            
            # Should show greeting card
            mock_message.answer.assert_called_once()
            
            # Should not call the handler
            mock_handler.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_unlinked_status_shows_greeting(self, middleware, mock_message, mock_handler, mock_data):
        """Test that unlinked status shows greeting card."""
        # Mock the answer method
        mock_message.answer = AsyncMock()
        
        with patch('bot.profiles.profiles.get_profile_by_chat_sync') as mock_get_profile, \
             patch('bot.i18n.get_locale') as mock_get_locale:
            
            # Mock existing profile with unlinked status
            mock_get_profile.return_value = {"status": "unlinked"}
            mock_get_locale.return_value = "en"
            
            result = await middleware(mock_handler, mock_message, mock_data)
            
            # Should show greeting card
            mock_message.answer.assert_called_once()
            
            # Should not call the handler
            mock_handler.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_active_status_calls_handler(self, middleware, mock_message, mock_handler, mock_data):
        """Test that active status calls the handler."""
        with patch('bot.profiles.profiles.get_profile_by_chat_sync') as mock_get_profile, \
             patch('bot.handlers_gate.show_greeting_card') as mock_show:
            
            # Mock existing profile with active status
            mock_get_profile.return_value = {"status": "active"}
            
            result = await middleware(mock_handler, mock_message, mock_data)
            
            # Should call the handler
            mock_handler.assert_called_once_with(mock_message, mock_data)
            
            # Should not show greeting card
            mock_show.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_no_status_field_shows_greeting(self, middleware, mock_message, mock_handler, mock_data):
        """Test that profiles without status field show greeting card."""
        # Mock the answer method
        mock_message.answer = AsyncMock()
        
        with patch('bot.profiles.profiles.get_profile_by_chat_sync') as mock_get_profile, \
             patch('bot.i18n.get_locale') as mock_get_locale:
            
            # Mock existing profile without status field
            mock_get_profile.return_value = {"family_id": "test"}
            mock_get_locale.return_value = "en"
            
            result = await middleware(mock_handler, mock_message, mock_data)
            
            # Should show greeting card
            mock_message.answer.assert_called_once()
            
            # Should not call the handler
            mock_handler.assert_not_called()


class TestGateHandlers:
    """Test the gate handlers functionality."""
    
    @pytest.mark.asyncio
    async def test_show_greeting_card_message(self):
        """Test showing greeting card for a message."""
        from bot.handlers_gate import show_greeting_card
        
        mock_message = MagicMock()
        mock_message.chat = MagicMock()
        mock_message.chat.id = 12345
        mock_message.answer = AsyncMock()
        
        with patch('bot.handlers_gate.get_locale') as mock_get_locale:
            mock_get_locale.return_value = "en"
            
            await show_greeting_card(mock_message)
            
            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args
            assert "I'm Silli. Choose an option." in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_show_greeting_card_message_pt_br(self):
        """Test showing greeting card for a message in Portuguese."""
        from bot.handlers_gate import show_greeting_card
        
        mock_message = MagicMock()
        mock_message.chat = MagicMock()
        mock_message.chat.id = 12345
        mock_message.answer = AsyncMock()
        
        with patch('bot.handlers_gate.get_locale') as mock_get_locale:
            mock_get_locale.return_value = "pt_br"
            
            await show_greeting_card(mock_message)
            
            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args
            assert "Sou Silli. Escolha uma opção." in call_args[0][0]
