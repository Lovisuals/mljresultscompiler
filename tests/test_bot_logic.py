import unittest
from unittest.mock import MagicMock, AsyncMock
from telegram import Update, User, Message, Chat
from telegram.ext import ContextTypes
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from telegram_bot import TelegramBotHandler, SELECTING_FORMAT

class TestBotHandlers(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.handler = TelegramBotHandler("fake_token")
        self.user = User(id=123, first_name="Test", is_bot=False)
        self.chat = Chat(id=123, type="private")
        
    async def test_consolidate_command_no_files(self):
        """Test that /consolidate reports no files if session is empty."""
        # Mock update
        update = MagicMock(spec=Update)
        update.effective_user = self.user
        update.message = AsyncMock(spec=Message)
        
        # Mock context
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        
        # Mock session manager (which is global in telegram_bot.py)
        import telegram_bot
        telegram_bot.session_manager.clear_session(123)
        
        # Run command
        result = await self.handler.consolidate_command(update, context)
        
        # Verify
        update.message.reply_text.assert_called_with(
            "📁 No files uploaded yet.\nPlease send at least one test file to get started."
        )
        self.assertEqual(result, SELECTING_FORMAT)

if __name__ == '__main__':
    unittest.main()
