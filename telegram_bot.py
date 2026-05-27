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
from telegram.error import TelegramError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import core modules
from src.excel_processor import ExcelProcessor
from src.session_manager import SessionManager, WorkflowAgent, ConversationalSession

# Optional imports with graceful fallback
try:
    from src.intent_engine import IntentEngine
    INTENT_ENGINE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Intent Engine not available: {e}")
    INTENT_ENGINE_AVAILABLE = False

try:
    from src.document_parser import UniversalDocumentParser
    DOCUMENT_PARSER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Document Parser not available: {e}")
    DOCUMENT_PARSER_AVAILABLE = False

try:
    from src.agent_router import AgentRouter
    AGENT_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Agent Router not available: {e}")
    AGENT_ROUTER_AVAILABLE = False

try:
    from config import ConversationalConfig
    CONFIG_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Conversational Config not available: {e}")
    CONFIG_AVAILABLE = False

CONVERSATIONAL_ENABLED = INTENT_ENGINE_AVAILABLE and DOCUMENT_PARSER_AVAILABLE and AGENT_ROUTER_AVAILABLE and CONFIG_AVAILABLE

# Load environment variables
load_dotenv(dotenv_path='.env')

# Conversation states
SELECTING_FORMAT = 1
CONFIRMING_PREVIEW = 2
SELECTING_OUTPUT_FORMAT = 3

# Initialize session manager
session_manager = SessionManager()


class TelegramBotHandler:
    """Main handler for Telegram bot operations"""

    def __init__(self, token: str):
        self.token = token
        self.bot_token = token

        # Initialize optional components if available
        if INTENT_ENGINE_AVAILABLE:
            try:
                self.intent_engine = IntentEngine()
            except Exception as e:
                logger.warning(f"Could not initialize intent engine: {e}")
                self.intent_engine = None
        else:
            self.intent_engine = None

        if DOCUMENT_PARSER_AVAILABLE:
            try:
                self.document_parser = UniversalDocumentParser()
            except Exception as e:
                logger.warning(f"Could not initialize document parser: {e}")
                self.document_parser = None
        else:
            self.document_parser = None

        if AGENT_ROUTER_AVAILABLE:
            try:
                self.agent_router = AgentRouter()
            except Exception as e:
                logger.warning(f"Could not initialize agent router: {e}")
                self.agent_router = None
        else:
            self.agent_router = None

        if CONFIG_AVAILABLE:
            try:
                self.conversational_config = ConversationalConfig()
            except Exception as e:
                logger.warning(f"Could not initialize conversational config: {e}")
                self.conversational_config = None
        else:
            self.conversational_config = None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /start command - initialize user session"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "User"

        # Initialize session
        session_manager.get_session(user_id)

        welcome_text = (
            f"🤖 <b>Welcome to MLJ Results Compiler, {username}!</b>\n\n"
            f"I help you consolidate test results from multiple Excel files.\n\n"
            f"<b>How to use me:</b>\n"
            f"1️⃣ Send me your test files (Excel .xlsx format)\n"
            f"2️⃣ Each file should be named with test number (e.g., <code>Test 1.xlsx</code>)\n"
            f"3️⃣ Type <code>/consolidate</code> when you've sent all files\n"
            f"4️⃣ Review the preview and confirm\n"
            f"5️⃣ Download your consolidated results\n\n"
            f"<b>File Requirements:</b>\n"
            f"• Must have a sheet named 'Responses'\n"
            f"• Must contain columns: <b>Full Name</b>, <b>Email</b>, <b>Result</b>\n\n"
            f"📤 <b>Send your first test file now!</b>"
        )

        await update.message.reply_text(welcome_text, parse_mode="HTML")
        logger.info(f"User {user_id} (@{username}) started the bot")
        return SELECTING_FORMAT

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /help command"""
        user_id = update.effective_user.id

        help_text = (
            "📚 <b>MLJ Results Compiler - Help Guide</b>\n\n"
            "<b>Commands:</b>\n"
            "• /start - Start the bot and initialize session\n"
            "• /consolidate - Process uploaded files and generate results\n"
            "• /help - Show this help message\n"
            "• /cancel - Cancel current operation\n\n"
            "<b>How to use:</b>\n"
            "1. Send Excel files (.xlsx) with test results\n"
            "2. Files should be named with test number (e.g., Test_1.xlsx, Test_2.xlsx)\n"
            "3. Each file must have a 'Responses' sheet\n"
            "4. Required columns: Full Name, Email, Result\n"
            "5. Type /consolidate when all files are uploaded\n"
            "6. Review the preview and confirm\n"
            "7. Download your consolidated Excel report\n\n"
            "<b>Features:</b>\n"
            "• Automatic test number detection from filename\n"
            "• Intelligent column mapping (works with various naming conventions)\n"
            "• Participation-based bonus calculation\n"
            "• Color-coded Excel output\n"
            "• Data validation and integrity checks\n\n"
            "<b>Need help?</b>\n"
            "Contact your system administrator for assistance."
        )

        await update.effective_message.reply_text(help_text, parse_mode="HTML")
        logger.info(f"User {user_id} requested help")
        return SELECTING_FORMAT

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /cancel command - clear session"""
        user_id = update.effective_user.id
        self._cleanup_session(user_id)

        await update.effective_message.reply_text(
            "❌ <b>Operation cancelled</b>\n\n"
            "Your session has been cleared. Use /start to begin again.",
            parse_mode="HTML"
        )
        logger.info(f"User {user_id} cancelled operation")
        return ConversationHandler.END

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle uploaded Excel files"""
        user_id = update.effective_user.id

        try:
            document = update.message.document
            logger.info(f"User {user_id}: Document received: {document.file_name}")

            # Validate file type
            if not document.file_name.lower().endswith('.xlsx'):
                await update.message.reply_text(
                    "❌ <b>Unsupported file type</b>\n\n"
                    "Please send <code>.xlsx</code> Excel files only.\n\n"
                    "Other formats (PDF, CSV, images) are not supported for consolidation.",
                    parse_mode="HTML"
                )
                return SELECTING_FORMAT

            # Get or create session
            session = session_manager.get_session(user_id)
            temp_dir = Path(session['temp_dir'])
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Download the file
            try:
                file = await context.bot.get_file(document.file_id)
                file_path = temp_dir / document.file_name
                await file.download_to_drive(file_path)
                logger.info(f"User {user_id}: File downloaded to {file_path}")
            except Exception as e:
                logger.error(f"User {user_id}: Failed to download file: {e}", exc_info=True)
                await update.message.reply_text(
                    f"❌ Failed to download file: {str(e)}\n\nPlease try again.",
                    parse_mode="HTML"
                )
                return SELECTING_FORMAT

            # Extract test number from filename
            test_num = self._extract_test_number(document.file_name)
            logger.info(f"User {user_id}: Extracted test number: {test_num}")

            if test_num is None:
                await update.message.reply_text(
                    "⚠️ <b>Could not detect test number</b>\n\n"
                    "Please name your file with a number, for example:\n"
                    "• <code>Test 1.xlsx</code>\n"
                    "• <code>Test_2.xlsx</code>\n"
                    "• <code>3.xlsx</code>\n"
                    "• <code>TEST_4_Results.xlsx</code>\n\n"
                    "Rename the file and send it again.",
                    parse_mode="HTML"
                )
                # Clean up the downloaded file
                try:
                    file_path.unlink()
                except:
                    pass
                return SELECTING_FORMAT

            # Check for duplicate test number
            uploaded_files = session_manager.get_files_for_consolidation(user_id)
            if test_num in uploaded_files:
                await update.message.reply_text(
                    f"⚠️ <b>Test {test_num} already uploaded</b>\n\n"
                    f"You already sent Test {test_num}. The first file is kept as authoritative.\n\n"
                    f"If you need to replace it, please use /cancel and start over.",
                    parse_mode="HTML"
                )
                # Delete the duplicate file
                try:
                    file_path.unlink()
                except:
                    pass
                return SELECTING_FORMAT

            # Add file to session
            try:
                summary = session_manager.add_file(user_id, str(file_path), test_num)
                logger.info(f"User {user_id}: Added Test {test_num} to session")
            except Exception as e:
                logger.error(f"User {user_id}: Error adding file to session: {e}", exc_info=True)
                await update.message.reply_text(
                    f"❌ Error processing file: {str(e)}\n\nPlease try again.",
                    parse_mode="HTML"
                )
                return SELECTING_FORMAT

            # Get updated file list
            session = session_manager.get_session(user_id)
            uploaded = session.get('uploaded_files', {})
            file_count = len(uploaded)
            file_list = ', '.join(f'Test {n}' for n in sorted(uploaded.keys()))

            await update.message.reply_text(
                f"✅ <b>Test {test_num} received!</b>\n\n"
                f"📁 Files uploaded: <b>{file_count}</b> ({file_list})\n\n"
                f"📤 Send more files or tap /consolidate when ready.",
                parse_mode="HTML"
            )

            return SELECTING_FORMAT

        except Exception as e:
            logger.error(f"User {user_id}: Unexpected error in handle_document: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Something went wrong processing your file.\n\n"
                "Please try sending it again or use /start to begin a new session.",
                parse_mode="HTML"
            )
            return SELECTING_FORMAT

    @staticmethod
    def _extract_test_number(filename: str) -> Optional[int]:
        """Extract test number from filename using regex patterns"""
        import re

        name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename

        # Pattern 1: Test X, Test_X, TestX
        match = re.search(r'[Tt]est\s*[_\-]?\s*(\d+)', name_without_ext)
        if match:
            return int(match.group(1))

        # Pattern 2: Just a number in the filename
        match = re.search(r'(\d+)', name_without_ext)
        if match:
            return int(match.group(1))

        return None

    async def consolidate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /consolidate command - show format selection"""
        user_id = update.effective_user.id

        session = session_manager.get_session(user_id)
        uploaded_files = session_manager.get_files_for_consolidation(user_id)

        if not uploaded_files:
            await update.message.reply_text(
                "⚠️ <b>No files uploaded yet</b>\n\n"
                "Please send your test Excel files first, then use /consolidate.\n\n"
                "Use /start for instructions on how to format your files.",
                parse_mode="HTML"
            )
            return SELECTING_FORMAT

        return await self._show_format_selection(update, context)

    async def _show_format_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Show format selection keyboard"""
        keyboard = [
            [InlineKeyboardButton("📊 Download Excel", callback_data='format_xlsx')],
            [InlineKeyboardButton("❌ Cancel", callback_data='format_cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.effective_message.reply_text(
            "📋 <b>Ready to consolidate!</b>\n\n"
            "Choose your output format:",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )

        return SELECTING_FORMAT

    async def format_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle format selection and start consolidation"""
        query = update.callback_query
        user_id = update.effective_user.id
        await query.answer()

        session = session_manager.get_session(user_id)
        uploaded_files = session_manager.get_files_for_consolidation(user_id)

        if not uploaded_files:
            await query.edit_message_text(
                "❌ No files found. Please upload test files first using /start"
            )
            return ConversationHandler.END

        if query.data == 'format_cancel' or query.data == 'cancel':
            await query.edit_message_text("❌ Operation cancelled. Use /start to begin again.")
            session_manager.clear_session(user_id)
            return ConversationHandler.END

        format_choice = query.data.replace('format_', '')

        try:
            await query.edit_message_text(
                "⏳ <b>Processing your files...</b>\n\n"
                "• Loading test data\n"
                "• Consolidating results\n"
                "• Calculating participation bonuses\n"
                "• Generating preview\n\n"
                "<i>This may take a moment...</i>",
                parse_mode="HTML"
            )

            input_dir = Path(session['temp_dir'])
            output_dir = Path(tempfile.mkdtemp())

            logger.info(f"User {user_id}: Processing files from {input_dir}")
            logger.info(f"Uploaded files: {list(uploaded_files.keys())}")

            # Verify files exist
            existing_files = []
            for test_num, file_path in uploaded_files.items():
                if Path(file_path).exists():
                    existing_files.append(test_num)
                else:
                    logger.warning(f"User {user_id}: File for Test {test_num} not found at {file_path}")

            if not existing_files:
                await query.edit_message_text(
                    "❌ No valid test files found. Please upload files again using /start"
                )
                session_manager.clear_session(user_id)
                return ConversationHandler.END

            # Create processor and load tests
            try:
                processor = ExcelProcessor(str(input_dir), str(output_dir))
                logger.info(f"User {user_id}: Created ExcelProcessor")
            except Exception as e:
                logger.error(f"User {user_id}: Failed to create ExcelProcessor: {e}", exc_info=True)
                raise

            loaded = processor.load_all_tests()
            logger.info(f"User {user_id}: Successfully loaded {loaded} test files")

            if loaded == 0:
                logger.error(f"User {user_id}: No valid test files found in {input_dir}")
                await query.edit_message_text(
                    "❌ <b>No valid test files could be processed</b>\n\n"
                    "Please ensure:\n"
                    "• Files are in .xlsx format\n"
                    "• Files have a 'Responses' sheet\n"
                    "• Files contain 'Full Name', 'Email', and 'Result' columns\n\n"
                    "Use /start to upload files again.",
                    parse_mode="HTML"
                )
                session_manager.clear_session(user_id)
                return ConversationHandler.END

            # Validate data integrity
            validation_report = processor.validate_data_integrity()
            context.user_data['validation_report'] = validation_report

            # Consolidate results
            consolidated_data = processor.consolidate_results()
            logger.info(f"User {user_id}: Consolidation returned {len(consolidated_data)} participants")

            if not consolidated_data:
                await query.edit_message_text(
                    "❌ <b>Consolidation failed</b>\n\n"
                    "No participant data could be extracted from your files.\n\n"
                    "Please check that your files contain valid participant data.",
                    parse_mode="HTML"
                )
                session_manager.clear_session(user_id)
                return ConversationHandler.END

            # Store data for later use
            context.user_data['consolidated_data'] = consolidated_data
            context.user_data['processor'] = processor
            context.user_data['output_dir'] = str(output_dir)
            context.user_data['format_choice'] = format_choice

            # Generate preview
            preview_image_path = processor.generate_preview_image(consolidated_data, max_rows=10)

            # Build warning text
            warnings_text = ""
            if validation_report:
                missing_count = len(validation_report.get('missing_participants', []))
                name_mismatch_count = len(validation_report.get('name_mismatches', []))
                duplicate_count = len(validation_report.get('duplicate_scores', []))

                if missing_count:
                    warnings_text += f"\n⚠️ Missing scores: {missing_count} participant(s)"
                if name_mismatch_count:
                    warnings_text += f"\n🔴 Name conflicts: {name_mismatch_count} (different names for same email)"
                if duplicate_count:
                    warnings_text += f"\n❓ Identical scores: {duplicate_count} participant(s)"

            caption = f"📊 <b>Consolidation Preview</b>\n\n👥 Participants: <b>{len(consolidated_data)}</b>"
            if warnings_text:
                caption += warnings_text
            caption += "\n\nTap a button below to continue."

            keyboard = [
                [
                    InlineKeyboardButton("✅ Looks Good!", callback_data='preview_confirm'),
                    InlineKeyboardButton("🔍 Full Data", callback_data='preview_full'),
                ],
                [InlineKeyboardButton("❌ Cancel", callback_data='preview_cancel')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            if preview_image_path and preview_image_path.exists():
                context.user_data['preview_image_path'] = str(preview_image_path)
                with open(preview_image_path, 'rb') as photo_file:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=photo_file,
                        caption=caption,
                        reply_markup=reply_markup,
                        parse_mode="HTML"
                    )
                try:
                    await query.delete_message()
                except:
                    pass
            else:
                # Fallback to text preview
                preview = self._generate_preview_text(consolidated_data, validation_report=validation_report)
                await query.edit_message_text(
                    preview,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )

            return CONFIRMING_PREVIEW

        except Exception as e:
            logger.error(f"User {user_id}: Error processing files: {str(e)}", exc_info=True)
            await query.edit_message_text(
                f"❌ <b>Error processing files</b>\n\n{str(e)}\n\nPlease try again or contact support.",
                parse_mode="HTML"
            )
            self._cleanup_session(user_id)
            return ConversationHandler.END

    def _generate_preview_text(self, consolidated_data: Dict, max_rows: int = 10, validation_report: Dict = None) -> str:
        """Generate text preview of consolidated data"""
        if not consolidated_data:
            return "❌ No data to preview"

        total_participants = len(consolidated_data)

        # Extract test numbers
        test_nums = set()
        for data in consolidated_data.values():
            for key in data.keys():
                if key.startswith('test_') and key.endswith('_score'):
                    test_nums.add(int(key.split('_')[1]))
        test_nums = sorted(test_nums)

        preview = f"""
📊 **CONSOLIDATION PREVIEW**

📈 **Summary:**
• Total Participants: {total_participants}
• Tests Consolidated: {', '.join(f'Test {t}' for t in test_nums)}
"""

        # Add warnings from validation report
        if validation_report:
            missing = validation_report.get('missing_participants', [])
            if missing:
                preview += f"\n⚠️ **MISSING SCORES:** {len(missing)} participant(s)"
                for item in missing[:3]:
                    preview += f"\n   • {item['name']} - missing in Test {item['missing_in_test']}"
                if len(missing) > 3:
                    preview += f"\n   ... and {len(missing) - 3} more"

            name_mismatches = validation_report.get('name_mismatches', [])
            if name_mismatches:
                preview += f"\n🔴 **NAME MISMATCH:** {len(name_mismatches)} conflict(s)"
                for item in name_mismatches[:2]:
                    preview += f"\n   • {item['email']}: Test 1='{item['test_1_name']}' vs Test {item['test_num']}='{item['conflicting_name']}'"

        preview += f"\n\n📋 **First {min(max_rows, total_participants)} Records:**\n"

        for idx, (email, data) in enumerate(consolidated_data.items()):
            if idx >= max_rows:
                break

            name = data['name']
            scores = []
            for test_num in test_nums:
                score = data.get(f'test_{test_num}_score')
                if score is not None:
                    scores.append(f"T{test_num}:{score}")
                else:
                    scores.append(f"T{test_num}:—")

            score_str = " | ".join(scores)
            preview += f"\n{idx+1}. {name}\n   {score_str}"

        if total_participants > max_rows:
            preview += f"\n\n... and {total_participants - max_rows} more participants"

        preview += "\n\n✅ **Look correct?**"
        return preview

    async def handle_preview_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle preview button actions"""
        query = update.callback_query
        user_id = update.effective_user.id
        await query.answer()

        action = query.data.split('_')[1] if '_' in query.data else query.data

        if action == 'cancel':
            try:
                await query.delete_message()
            except:
                await query.edit_message_text("❌ Operation cancelled")
            self._cleanup_session(user_id)
            return ConversationHandler.END

        elif action == 'full':
            consolidated_data = context.user_data.get('consolidated_data', {})
            validation_report = context.user_data.get('validation_report')
            processor = context.user_data.get('processor')

            if processor:
                full_image_path = processor.generate_preview_image(consolidated_data, max_rows=999)
                if full_image_path and full_image_path.exists():
                    try:
                        await query.delete_message()
                        with open(full_image_path, 'rb') as photo_file:
                            await context.bot.send_photo(
                                chat_id=update.effective_chat.id,
                                photo=photo_file,
                                caption="📊 <b>Full data preview</b> — all participants shown",
                                parse_mode="HTML"
                            )
                        return CONFIRMING_PREVIEW
                    except Exception as e:
                        logger.error(f"Error sending full image: {str(e)}")

            full_preview = self._generate_preview_text(consolidated_data, max_rows=999, validation_report=validation_report)
            await query.edit_message_text(full_preview, parse_mode="Markdown")
            return CONFIRMING_PREVIEW

        elif action == 'confirm':
            try:
                await query.delete_message()
            except:
                pass

            keyboard = [
                [InlineKeyboardButton("📊 Download Excel", callback_data='format_xlsx')],
                [InlineKeyboardButton("❌ Cancel", callback_data='format_cancel')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="📋 <b>Great!</b> Choose your output format:",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            return SELECTING_OUTPUT_FORMAT

        return CONFIRMING_PREVIEW

    async def format_confirmed(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle format confirmation and generate output file"""
        query = update.callback_query
        user_id = update.effective_user.id
        await query.answer()

        if query.data == 'format_cancel' or query.data == 'cancel':
            await query.edit_message_text("❌ Operation cancelled. Use /start to begin again.")
            self._cleanup_session(user_id)
            return ConversationHandler.END

        format_choice = query.data.replace('format_', '')

        try:
            consolidated_data = context.user_data.get('consolidated_data', {})
            processor = context.user_data.get('processor')
            output_dir = Path(context.user_data.get('output_dir', tempfile.gettempdir()))

            if not consolidated_data or not processor:
                await query.edit_message_text("❌ Session expired. Please use /start to begin again.")
                return ConversationHandler.END

            # Currently only Excel is fully supported
            if format_choice != 'xlsx':
                await query.edit_message_text(
                    f"⚠️ {format_choice.upper()} export is not yet available.\n"
                    f"Generating Excel instead..."
                )
                format_choice = 'xlsx'

            await query.edit_message_text("⏳ <b>Generating your report...</b>", parse_mode="HTML")

            output_file = output_dir / 'Consolidated_Results.xlsx'
            success = processor.save_consolidated_file(consolidated_data, output_file.name)

            if not success or not output_file.exists():
                await query.edit_message_text(
                    "❌ Failed to generate report. Please try again."
                )
                self._cleanup_session(user_id)
                return ConversationHandler.END

            # Get test numbers for summary
            test_nums = set()
            for data in consolidated_data.values():
                for key in data.keys():
                    if key.startswith('test_') and key.endswith('_score'):
                        test_nums.add(int(key.split('_')[1]))
            test_nums = sorted(test_nums)

            # Send the file
            with open(output_file, 'rb') as f:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=f,
                    filename=output_file.name,
                    caption=f"✅ <b>Consolidation Complete!</b>\n\n👥 {len(consolidated_data)} participants\n📝 {len(test_nums)} tests merged",
                    parse_mode="HTML"
                )

            logger.info(f"User {user_id}: Delivered consolidated results ({len(consolidated_data)} participants, {len(test_nums)} tests)")

            # Clean up
            self._cleanup_session(user_id)
            return ConversationHandler.END

        except Exception as e:
            logger.error(f"User {user_id}: Error generating file: {str(e)}", exc_info=True)
            await query.edit_message_text(
                f"❌ Error generating report: {str(e)}\n\nPlease try again."
            )
            self._cleanup_session(user_id)
            return ConversationHandler.END

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle regular text messages (non-command)"""
        if not update.message or not update.message.text:
            return

        user_id = update.effective_user.id
        message_text = update.message.text

        if message_text.startswith('/'):
            return

        logger.info(f"User {user_id}: Received message: {message_text}")

        # Use conversational AI if available
        if CONVERSATIONAL_ENABLED and self.intent_engine:
            try:
                conv_session = ConversationalSession(session_manager, user_id)
                conv_session.add_message(message_text, role='user')

                intent_result = self.intent_engine.detect_intent(message_text)
                intent = intent_result['intent']
                confidence = intent_result['confidence']

                logger.info(f"User {user_id}: Detected intent: {intent} (confidence: {confidence:.2%})")

                if confidence >= 0.5:
                    conv_session.update_intent(intent, confidence)

                response = self._generate_contextual_response(intent, intent_result, conv_session)

                await update.message.reply_text(response, parse_mode="Markdown")
                conv_session.add_message(response, role='bot')

            except Exception as e:
                logger.error(f"User {user_id}: Error in conversational handling: {e}")
                await update.message.reply_text(
                    "I'm here to help you consolidate test results!\n\n"
                    "📤 Send me Excel files (.xlsx) with your test results.\n"
                    "📝 Type /help for instructions.\n"
                    "🚀 Type /consolidate when you're ready to process."
                )
        else:
            # Simple fallback response
            await update.message.reply_text(
                "I'm here to help you consolidate test results!\n\n"
                "📤 Send me Excel files (.xlsx) with your test results.\n"
                "📝 Type /help for instructions.\n"
                "🚀 Type /consolidate when you're ready to process."
            )

    def _generate_contextual_response(self, intent: str, intent_result: dict,
                                     conv_session: ConversationalSession) -> str:
        """Generate contextual response based on detected intent"""
        doc_count = conv_session.get_document_count()

        if intent == 'test_consolidation':
            if doc_count == 0:
                return (
                    "📊 **Test Consolidation Assistant**\n\n"
                    "I can help you merge multiple test result files into one consolidated report.\n\n"
                    "**To get started:**\n"
                    "1. Send me your Excel files (Test 1, Test 2, etc.)\n"
                    "2. Each file should have a 'Responses' sheet\n"
                    "3. Type `/consolidate` when you're ready\n\n"
                    "Go ahead and send your first test file!"
                )
            else:
                return (
                    f"📊 **Test Consolidation in Progress**\n\n"
                    f"✅ You've uploaded {doc_count} file(s)\n\n"
                    f"You can:\n"
                    f"• Upload more test files\n"
                    f"• Type `/consolidate` to process now"
                )

        elif intent == 'invoice_processing':
            return (
                "📄 **Document Processing**\n\n"
                "I specialize in test result consolidation. For invoice processing, "
                "please ensure your files follow the test result format with "
                "'Full Name', 'Email', and 'Result' columns."
            )

        elif intent in ('image_extraction', 'table_merge', 'data_cleaning', 'report_generation'):
            return (
                f"🔧 **{intent.replace('_', ' ').title()}**\n\n"
                f"✅ This feature is available through test consolidation!\n\n"
                f"📤 Send me your Excel files and I'll process them.\n"
                f"You can upload multiple files for consolidation."
            )

        elif intent == 'unknown':
            suggestions = intent_result.get('suggestions', [])
            response = "I'm here to help! 🤖\n\n"
            if suggestions:
                response += "Here's what I can do:\n" + "\n".join(suggestions)
            else:
                response += (
                    "**I can help you with:**\n"
                    "• Consolidating test results from multiple Excel files\n"
                    "• Calculating participation bonuses\n"
                    "• Generating color-coded reports\n\n"
                    "📤 Send me your test files to get started!"
                )
            return response

        return (
            "I'm your test results consolidation assistant!\n\n"
            "📤 Send me Excel files (.xlsx) with your test results.\n"
            "📝 Type /help for detailed instructions.\n"
            "🚀 Type /consolidate when you're ready."
        )

    def _cleanup_session(self, user_id: int) -> None:
        """Clean up user session and temporary files"""
        try:
            session_manager.clear_session(user_id)
            logger.info(f"User {user_id}: Session cleaned up")
        except Exception as e:
            logger.error(f"User {user_id}: Error cleaning up session: {e}")


def build_application(token: str) -> Application:
    """Build and configure the Telegram application"""
    application = Application.builder().token(token).build()
    handler = TelegramBotHandler(token)

    # Conversation handler for the main workflow
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", handler.start),
            CommandHandler("consolidate", handler.consolidate_command),
            MessageHandler(filters.Document.FileExtension(["xlsx", "XLSX"]), handler.handle_document),
        ],
        states={
            SELECTING_FORMAT: [
                MessageHandler(filters.Document.FileExtension(["xlsx", "XLSX"]), handler.handle_document),
                CallbackQueryHandler(handler.format_selected),
                CommandHandler("consolidate", handler.consolidate_command),
            ],
            CONFIRMING_PREVIEW: [
                CallbackQueryHandler(handler.handle_preview_action),
            ],
            SELECTING_OUTPUT_FORMAT: [
                CallbackQueryHandler(handler.format_confirmed),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", handler.cancel),
            CommandHandler("start", handler.start),
            CommandHandler("help", handler.help_command),
        ],
    )

    application.add_handler(conv_handler)

    # Standalone command handlers
    application.add_handler(CommandHandler("help", handler.help_command))
    application.add_handler(CommandHandler("start", handler.start))
    application.add_handler(CommandHandler("consolidate", handler.consolidate_command))
    application.add_handler(CommandHandler("cancel", handler.cancel))

    # Message handler for conversational AI (non-commands)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handler.handle_message)
    )

    return application


def main():
    """Main entry point"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')

    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        raise ValueError("Please set TELEGRAM_BOT_TOKEN in .env file")

    application = build_application(token)

    logger.info("Starting MLJ Results Compiler Telegram Bot (polling mode)")
    logger.info("Bot is running... Press Ctrl+C to stop")

    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped with error: {e}")
        raise


if __name__ == "__main__":
    main()