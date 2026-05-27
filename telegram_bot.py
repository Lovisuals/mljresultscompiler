#!/usr/bin/env python3
"""
MLJ Results Compiler Telegram Bot
Minimal version - only responds to commands, ignores random messages
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from src.excel_processor import ExcelProcessor
from src.session_manager import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Conversation states
WAITING_FOR_FILES = 1
CONFIRMING_PREVIEW = 2
SELECTING_OUTPUT = 3

# Initialize session manager
session_manager = SessionManager()


class ResultsBot:
    """Minimal Telegram bot for test results consolidation"""

    def __init__(self, token: str):
        self.token = token

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /start command"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "User"

        # Initialize session
        session_manager.get_session(user_id)

        welcome_text = (
            f"🤖 <b>MLJ Results Compiler</b>\n\n"
            f"Welcome {username}!\n\n"
            f"<b>How to use:</b>\n"
            f"1. Send Excel files (.xlsx) named like: Test 1.xlsx, Test 2.xlsx\n"
            f"2. Type <code>/consolidate</code> when done\n"
            f"3. Review preview and confirm\n"
            f"4. Download consolidated results\n\n"
            f"<b>File requirements:</b>\n"
            f"• Sheet named 'Responses'\n"
            f"• Columns: Full Name, Email, Result\n\n"
            f"Send your first test file now!"
        )

        await update.message.reply_text(welcome_text, parse_mode="HTML")
        logger.info(f"User {user_id} started bot")
        return WAITING_FOR_FILES

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /help command"""
        help_text = (
            "📚 <b>MLJ Results Compiler - Help</b>\n\n"
            "<b>Commands:</b>\n"
            "• /start - Start a new session\n"
            "• /consolidate - Process uploaded files\n"
            "• /cancel - Clear session\n"
            "• /help - Show this message\n\n"
            "<b>File naming examples:</b>\n"
            "• Test 1.xlsx\n"
            "• Test_2.xlsx\n"
            "• 3.xlsx\n"
            "• TEST_4_Results.xlsx\n\n"
            "<b>Required columns in Excel:</b>\n"
            "• Full Name (or Name, Student Name)\n"
            "• Email (or Email Address)\n"
            "• Result (or Score, Marks, %)\n\n"
            "<b>Output:</b>\n"
            "• Color-coded Excel file\n"
            "• Participation bonus included\n"
            "• PASS/FAIL based on 50% threshold"
        )

        await update.message.reply_text(help_text, parse_mode="HTML")
        logger.info(f"User {update.effective_user.id} requested help")
        return WAITING_FOR_FILES

    async def cmd_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /cancel command - clear session"""
        user_id = update.effective_user.id
        self._cleanup_session(user_id)

        await update.message.reply_text(
            "❌ <b>Session cleared</b>\n\nUse /start to begin again.",
            parse_mode="HTML"
        )
        logger.info(f"User {user_id} cancelled session")
        return ConversationHandler.END

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle uploaded Excel files"""
        user_id = update.effective_user.id

        try:
            document = update.message.document

            # Validate file type
            if not document.file_name.lower().endswith('.xlsx'):
                await update.message.reply_text(
                    "❌ Only <code>.xlsx</code> files are supported.\n\n"
                    "Please send an Excel file.",
                    parse_mode="HTML"
                )
                return WAITING_FOR_FILES

            # Get session
            session = session_manager.get_session(user_id)
            temp_dir = Path(session['temp_dir'])
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Download file
            file = await context.bot.get_file(document.file_id)
            file_path = temp_dir / document.file_name
            await file.download_to_drive(file_path)

            # Extract test number
            test_num = self._extract_test_number(document.file_name)

            if test_num is None:
                await update.message.reply_text(
                    "⚠️ <b>Could not detect test number</b>\n\n"
                    "Please name your file with a number, e.g.:\n"
                    "• <code>Test 1.xlsx</code>\n"
                    "• <code>Test_2.xlsx</code>\n"
                    "• <code>3.xlsx</code>",
                    parse_mode="HTML"
                )
                file_path.unlink()
                return WAITING_FOR_FILES

            # Check for duplicate test
            uploaded = session_manager.get_files_for_consolidation(user_id)
            if test_num in uploaded:
                await update.message.reply_text(
                    f"⚠️ <b>Test {test_num} already uploaded</b>\n\n"
                    f"First file kept as authoritative. Duplicate ignored.",
                    parse_mode="HTML"
                )
                file_path.unlink()
                return WAITING_FOR_FILES

            # Save file to session
            session_manager.add_file(user_id, str(file_path), test_num)

            # Get updated file list
            uploaded = session_manager.get_files_for_consolidation(user_id)
            file_list = ', '.join(f'Test {n}' for n in sorted(uploaded.keys()))

            await update.message.reply_text(
                f"✅ <b>Test {test_num} received!</b>\n\n"
                f"📁 Files: {file_list}\n\n"
                f"Send more files or type <code>/consolidate</code> when ready.",
                parse_mode="HTML"
            )

            return WAITING_FOR_FILES

        except Exception as e:
            logger.error(f"Error handling document for user {user_id}: {e}")
            await update.message.reply_text(
                f"❌ Error: {str(e)[:200]}\n\nPlease try again."
            )
            return WAITING_FOR_FILES

    @staticmethod
    def _extract_test_number(filename: str) -> Optional[int]:
        """Extract test number from filename"""
        import re
        name = filename.rsplit('.', 1)[0]
        
        # Pattern: Test X, Test_X, TestX
        match = re.search(r'[Tt]est\s*[_\-]?\s*(\d+)', name)
        if match:
            return int(match.group(1))
        
        # Pattern: Just a number
        match = re.search(r'(\d+)', name)
        if match:
            return int(match.group(1))
        
        return None

    async def cmd_consolidate(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /consolidate command"""
        user_id = update.effective_user.id

        uploaded = session_manager.get_files_for_consolidation(user_id)

        if not uploaded:
            await update.message.reply_text(
                "⚠️ <b>No files uploaded</b>\n\n"
                "Please send your test Excel files first, then use /consolidate.",
                parse_mode="HTML"
            )
            return WAITING_FOR_FILES

        keyboard = [
            [InlineKeyboardButton("📊 Consolidate to Excel", callback_data='consolidate')],
            [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"📋 <b>Ready to consolidate</b>\n\n"
            f"Files: {', '.join(f'Test {n}' for n in sorted(uploaded.keys()))}\n\n"
            f"Proceed?",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )

        return WAITING_FOR_FILES

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle button callbacks"""
        query = update.callback_query
        user_id = update.effective_user.id
        await query.answer()

        if query.data == 'cancel':
            await query.edit_message_text("❌ Cancelled. Use /start to begin again.")
            self._cleanup_session(user_id)
            return ConversationHandler.END

        if query.data == 'consolidate':
            await query.edit_message_text("⏳ <b>Processing files...</b>", parse_mode="HTML")

            try:
                session = session_manager.get_session(user_id)
                uploaded = session_manager.get_files_for_consolidation(user_id)

                input_dir = Path(session['temp_dir'])
                output_dir = Path(tempfile.mkdtemp())

                # Process files
                processor = ExcelProcessor(str(input_dir), str(output_dir))
                loaded = processor.load_all_tests()

                if loaded == 0:
                    await query.edit_message_text(
                        "❌ <b>No valid test files found</b>\n\n"
                        "Please ensure files have a 'Responses' sheet with 'Full Name', 'Email', and 'Result' columns.",
                        parse_mode="HTML"
                    )
                    self._cleanup_session(user_id)
                    return ConversationHandler.END

                # Consolidate
                consolidated = processor.consolidate_results()

                if not consolidated:
                    await query.edit_message_text(
                        "❌ <b>Consolidation failed</b>\n\nNo participant data found.",
                        parse_mode="HTML"
                    )
                    self._cleanup_session(user_id)
                    return ConversationHandler.END

                # Generate preview
                preview_path = processor.generate_preview_image(consolidated, max_rows=10)

                # Store for later
                context.user_data['consolidated'] = consolidated
                context.user_data['processor'] = processor
                context.user_data['output_dir'] = str(output_dir)

                # Send preview
                caption = f"📊 <b>Preview</b>\n\n👥 {len(consolidated)} participants\n\nProceed to download?"

                keyboard = [
                    [InlineKeyboardButton("✅ Download Excel", callback_data='download')],
                    [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                if preview_path and preview_path.exists():
                    with open(preview_path, 'rb') as photo:
                        await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=photo,
                            caption=caption,
                            reply_markup=reply_markup,
                            parse_mode="HTML"
                        )
                    await query.delete_message()
                else:
                    await query.edit_message_text(
                        f"📊 <b>Consolidation Preview</b>\n\n👥 {len(consolidated)} participants\n\nProceed?",
                        reply_markup=reply_markup,
                        parse_mode="HTML"
                    )

                return CONFIRMING_PREVIEW

            except Exception as e:
                logger.error(f"Consolidation error for user {user_id}: {e}")
                await query.edit_message_text(
                    f"❌ <b>Error</b>\n\n{str(e)[:300]}\n\nPlease try again.",
                    parse_mode="HTML"
                )
                self._cleanup_session(user_id)
                return ConversationHandler.END

        return WAITING_FOR_FILES

    async def download_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle download button"""
        query = update.callback_query
        user_id = update.effective_user.id
        await query.answer()

        if query.data == 'cancel':
            await query.edit_message_text("❌ Cancelled. Use /start to begin again.")
            self._cleanup_session(user_id)
            return ConversationHandler.END

        if query.data == 'download':
            await query.edit_message_text("⏳ <b>Generating your report...</b>", parse_mode="HTML")

            try:
                consolidated = context.user_data.get('consolidated', {})
                processor = context.user_data.get('processor')
                output_dir = Path(context.user_data.get('output_dir', tempfile.gettempdir()))

                if not consolidated or not processor:
                    await query.edit_message_text("❌ Session expired. Use /start to begin again.")
                    return ConversationHandler.END

                # Save file
                output_file = output_dir / 'Consolidated_Results.xlsx'
                success = processor.save_consolidated_file(consolidated, output_file.name)

                if not success or not output_file.exists():
                    await query.edit_message_text("❌ Failed to generate report. Please try again.")
                    return ConversationHandler.END

                # Get test numbers
                test_nums = set()
                for data in consolidated.values():
                    for key in data.keys():
                        if key.startswith('test_') and key.endswith('_score'):
                            test_nums.add(int(key.split('_')[1]))

                # Send file
                with open(output_file, 'rb') as f:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=f,
                        filename=f"Results_{len(consolidated)}_participants.xlsx",
                        caption=f"✅ <b>Complete!</b>\n\n👥 {len(consolidated)} participants\n📝 {len(test_nums)} tests",
                        parse_mode="HTML"
                    )

                logger.info(f"User {user_id}: Downloaded results ({len(consolidated)} participants)")

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="🔄 Use /start to begin a new session.",
                    parse_mode="HTML"
                )

                self._cleanup_session(user_id)
                return ConversationHandler.END

            except Exception as e:
                logger.error(f"Download error for user {user_id}: {e}")
                await query.edit_message_text(
                    f"❌ <b>Error generating report</b>\n\n{str(e)[:300]}",
                    parse_mode="HTML"
                )
                self._cleanup_session(user_id)
                return ConversationHandler.END

        return ConversationHandler.END

    def _cleanup_session(self, user_id: int) -> None:
        """Clean up user session"""
        try:
            session_manager.clear_session(user_id)
        except Exception as e:
            logger.error(f"Cleanup error for user {user_id}: {e}")

    # This method is intentionally empty - NO RESPONSE TO RANDOM MESSAGES
    async def ignore_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Ignore all non-command messages - bot does NOT respond"""
        return


def build_application(token: str) -> Application:
    """Build the bot application"""
    bot = ResultsBot(token)
    application = Application.builder().token(token).build()

    # Conversation handler for file upload workflow
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", bot.cmd_start),
            CommandHandler("consolidate", bot.cmd_consolidate),
            MessageHandler(filters.Document.ALL, bot.handle_document),
        ],
        states={
            WAITING_FOR_FILES: [
                CommandHandler("start", bot.cmd_start),
                CommandHandler("help", bot.cmd_help),
                CommandHandler("consolidate", bot.cmd_consolidate),
                CommandHandler("cancel", bot.cmd_cancel),
                MessageHandler(filters.Document.ALL, bot.handle_document),
                CallbackQueryHandler(bot.button_callback),
            ],
            CONFIRMING_PREVIEW: [
                CallbackQueryHandler(bot.download_callback),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", bot.cmd_cancel),
            CommandHandler("start", bot.cmd_start),
        ],
    )

    application.add_handler(conv_handler)

    # Standalone command handlers
    application.add_handler(CommandHandler("start", bot.cmd_start))
    application.add_handler(CommandHandler("help", bot.cmd_help))
    application.add_handler(CommandHandler("consolidate", bot.cmd_consolidate))
    application.add_handler(CommandHandler("cancel", bot.cmd_cancel))

    # CRITICAL: This handler ignores ALL non-command messages (no response)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, bot.ignore_message)
    )

    return application


def main():
    """Main entry point"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')

    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        raise ValueError("Please set TELEGRAM_BOT_TOKEN in .env file")

    application = build_application(token)

    logger.info("Starting MLJ Results Compiler Bot...")
    logger.info("Bot will ONLY respond to commands: /start, /help, /consolidate, /cancel")
    logger.info("Random text messages will be IGNORED")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
