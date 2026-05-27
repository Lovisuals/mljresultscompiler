#!/usr/bin/env python3
"""
MLJ Results Compiler Telegram Bot
Fixed version - Download button working properly
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

load_dotenv()

# Conversation states
WAITING_FOR_FILES = 1
PROCESSING_FILES = 2

session_manager = SessionManager()


class ResultsBot:
    """Telegram bot for test results consolidation"""

    def __init__(self, token: str):
        self.token = token

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /start command"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "User"

        session_manager.get_session(user_id)
        context.user_data.clear()  # Clear any old data

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
            "• 3.xlsx\n\n"
            "<b>Required columns in Excel:</b>\n"
            "• Full Name (or Name)\n"
            "• Email\n"
            "• Result (or Score, %)\n\n"
            "<b>Output:</b>\n"
            "• Color-coded Excel file\n"
            "• Participation bonus included\n"
            "• PASS/FAIL based on 50% threshold"
        )

        await update.message.reply_text(help_text, parse_mode="HTML")
        return WAITING_FOR_FILES

    async def cmd_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /cancel command"""
        user_id = update.effective_user.id
        self._cleanup_session(user_id)
        context.user_data.clear()

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

            if not document.file_name.lower().endswith('.xlsx'):
                await update.message.reply_text(
                    "❌ Only <code>.xlsx</code> files are supported.",
                    parse_mode="HTML"
                )
                return WAITING_FOR_FILES

            session = session_manager.get_session(user_id)
            temp_dir = Path(session['temp_dir'])
            temp_dir.mkdir(parents=True, exist_ok=True)

            file = await context.bot.get_file(document.file_id)
            file_path = temp_dir / document.file_name
            await file.download_to_drive(file_path)

            test_num = self._extract_test_number(document.file_name)

            if test_num is None:
                await update.message.reply_text(
                    "⚠️ <b>Could not detect test number</b>\n\n"
                    "Name your file with a number, e.g.: Test 1.xlsx",
                    parse_mode="HTML"
                )
                file_path.unlink()
                return WAITING_FOR_FILES

            uploaded = session_manager.get_files_for_consolidation(user_id)
            if test_num in uploaded:
                await update.message.reply_text(
                    f"⚠️ <b>Test {test_num} already uploaded</b> - ignored.",
                    parse_mode="HTML"
                )
                file_path.unlink()
                return WAITING_FOR_FILES

            session_manager.add_file(user_id, str(file_path), test_num)

            uploaded = session_manager.get_files_for_consolidation(user_id)
            file_list = ', '.join(f'Test {n}' for n in sorted(uploaded.keys()))

            await update.message.reply_text(
                f"✅ <b>Test {test_num} received!</b>\n\n"
                f"📁 Files: {file_list}\n\n"
                f"Type <code>/consolidate</code> when ready.",
                parse_mode="HTML"
            )

            return WAITING_FOR_FILES

        except Exception as e:
            logger.error(f"Error handling document: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)[:200]}")
            return WAITING_FOR_FILES

    @staticmethod
    def _extract_test_number(filename: str) -> Optional[int]:
        import re
        name = filename.rsplit('.', 1)[0]
        match = re.search(r'[Tt]est\s*[_\-]?\s*(\d+)', name)
        if match:
            return int(match.group(1))
        match = re.search(r'(\d+)', name)
        return int(match.group(1)) if match else None

    async def cmd_consolidate(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /consolidate command"""
        user_id = update.effective_user.id
        uploaded = session_manager.get_files_for_consolidation(user_id)

        if not uploaded:
            await update.message.reply_text(
                "⚠️ <b>No files uploaded</b>\n\nSend test files first.",
                parse_mode="HTML"
            )
            return WAITING_FOR_FILES

        keyboard = [
            [InlineKeyboardButton("📊 Consolidate", callback_data='consolidate')],
            [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = await update.message.reply_text(
            f"📋 <b>Ready to consolidate</b>\n\n"
            f"Files: {', '.join(f'Test {n}' for n in sorted(uploaded.keys()))}\n\n"
            f"Proceed?",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        
        # Store message ID for later reference
        context.user_data['consolidate_message_id'] = message.message_id
        
        return WAITING_FOR_FILES

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle button callbacks"""
        query = update.callback_query
        user_id = update.effective_user.id
        callback_data = query.data
        
        await query.answer()

        if callback_data == 'cancel':
            await query.edit_message_text("❌ Cancelled. Use /start to begin again.")
            self._cleanup_session(user_id)
            context.user_data.clear()
            return ConversationHandler.END

        if callback_data == 'consolidate':
            # Show processing message
            await query.edit_message_text("⏳ <b>Processing files...</b>", parse_mode="HTML")

            try:
                session = session_manager.get_session(user_id)
                uploaded = session_manager.get_files_for_consolidation(user_id)

                input_dir = Path(session['temp_dir'])
                output_dir = Path(tempfile.mkdtemp())

                processor = ExcelProcessor(str(input_dir), str(output_dir))
                loaded = processor.load_all_tests()

                if loaded == 0:
                    await query.edit_message_text(
                        "❌ <b>No valid test files found</b>\n\n"
                        "Ensure files have 'Responses' sheet with required columns.",
                        parse_mode="HTML"
                    )
                    self._cleanup_session(user_id)
                    return ConversationHandler.END

                consolidated = processor.consolidate_results()

                if not consolidated:
                    await query.edit_message_text(
                        "❌ <b>Consolidation failed</b>\n\nNo participant data found.",
                        parse_mode="HTML"
                    )
                    self._cleanup_session(user_id)
                    return ConversationHandler.END

                # Store data for download
                context.user_data['consolidated'] = consolidated
                context.user_data['processor'] = processor
                context.user_data['output_dir'] = str(output_dir)

                # Create download buttons
                keyboard = [
                    [InlineKeyboardButton("📥 Download Excel", callback_data='download_xlsx')],
                    [InlineKeyboardButton("❌ Cancel", callback_data='cancel_download')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                # Update message with success and download option
                await query.edit_message_text(
                    f"✅ <b>Consolidation Complete!</b>\n\n"
                    f"👥 <b>{len(consolidated)}</b> participants processed\n"
                    f"📊 Tests: {', '.join(f'Test {t}' for t in sorted(processor.test_data.keys()))}\n\n"
                    f"Click below to download your results:",
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )

                return WAITING_FOR_FILES  # Stay in waiting state for download button

            except Exception as e:
                logger.error(f"Consolidation error: {e}")
                await query.edit_message_text(
                    f"❌ <b>Error</b>\n\n{str(e)[:300]}", 
                    parse_mode="HTML"
                )
                self._cleanup_session(user_id)
                return ConversationHandler.END

        if callback_data == 'download_xlsx':
            # Generate and send the Excel file
            await query.edit_message_text("⏳ <b>Generating your Excel report...</b>", parse_mode="HTML")

            try:
                consolidated = context.user_data.get('consolidated')
                processor = context.user_data.get('processor')
                output_dir = Path(context.user_data.get('output_dir', tempfile.gettempdir()))

                if not consolidated or not processor:
                    await query.edit_message_text(
                        "❌ <b>Session expired</b>\n\nPlease use /start to begin again.",
                        parse_mode="HTML"
                    )
                    return ConversationHandler.END

                output_file = output_dir / 'Consolidated_Results.xlsx'
                success = processor.save_consolidated_file(consolidated, output_file.name)

                if not success or not output_file.exists():
                    await query.edit_message_text(
                        "❌ <b>Failed to generate report</b>\n\nPlease try again.",
                        parse_mode="HTML"
                    )
                    return ConversationHandler.END

                # Send the file
                with open(output_file, 'rb') as f:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=f,
                        filename=f"Consolidated_Results_{len(consolidated)}_participants.xlsx",
                        caption=f"✅ <b>Your consolidated results are ready!</b>\n\n"
                                f"👥 {len(consolidated)} participants\n\n"
                                f"Use /start to begin a new session.",
                        parse_mode="HTML"
                    )

                logger.info(f"User {user_id}: Downloaded results ({len(consolidated)} participants)")

                # Delete the processing message
                try:
                    await query.message.delete()
                except:
                    pass

                # Clean up
                self._cleanup_session(user_id)
                context.user_data.clear()
                return ConversationHandler.END

            except Exception as e:
                logger.error(f"Download error: {e}")
                await query.edit_message_text(
                    f"❌ <b>Error generating file</b>\n\n{str(e)[:300]}",
                    parse_mode="HTML"
                )
                self._cleanup_session(user_id)
                return ConversationHandler.END

        if callback_data == 'cancel_download':
            await query.edit_message_text(
                "❌ <b>Cancelled</b>\n\nUse /start to begin a new session.",
                parse_mode="HTML"
            )
            self._cleanup_session(user_id)
            context.user_data.clear()
            return ConversationHandler.END

        return WAITING_FOR_FILES

    def _cleanup_session(self, user_id: int) -> None:
        try:
            session_manager.clear_session(user_id)
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    async def ignore_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Ignore all non-command messages"""
        return


def build_application(token: str) -> Application:
    """Build the bot application"""
    bot = ResultsBot(token)
    application = Application.builder().token(token).build()

    # Single conversation handler
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
        },
        fallbacks=[
            CommandHandler("cancel", bot.cmd_cancel),
            CommandHandler("start", bot.cmd_start),
        ],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", bot.cmd_start))
    application.add_handler(CommandHandler("help", bot.cmd_help))
    application.add_handler(CommandHandler("consolidate", bot.cmd_consolidate))
    application.add_handler(CommandHandler("cancel", bot.cmd_cancel))
    
    # Ignore all non-command text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.ignore_message))

    return application


def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN')

    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found")
        raise ValueError("Please set TELEGRAM_BOT_TOKEN")

    application = build_application(token)
    logger.info("Starting MLJ Results Compiler Bot...")
    logger.info("Bot is running. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
