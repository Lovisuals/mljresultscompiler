"""
MLJ Results Compiler - Telegram Bot
Allows users to upload test files and get consolidated results via Telegram
Session-aware, agentic workflow: collect files → consolidate on demand
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import Dict
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

# Setup logging EARLY so it's available for import error handling
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from src.excel_processor import ExcelProcessor
from src.session_manager import SessionManager, WorkflowAgent, ConversationalSession
# Import conversational components (with fallback if not available)
try:
    from src.intent_engine import IntentEngine
    from src.document_parser import UniversalDocumentParser
    from src.agent_router import AgentRouter
    from config import ConversationalConfig
    CONVERSATIONAL_ENABLED = True
except ImportError as e:
    logger.warning(f"Conversational features not available: {e}")
    CONVERSATIONAL_ENABLED = False

# Load environment variables
load_dotenv(dotenv_path='.env')

# Conversation states
SELECTING_FORMAT = 1
CONFIRMING_PREVIEW = 2
SELECTING_OUTPUT_FORMAT = 3

# Global session manager (persists across requests)
session_manager = SessionManager()

class TelegramBotHandler:
    """Handles Telegram bot interactions"""
    
    def __init__(self, token):
        self.token = token
        self.bot_token = token
        
        # Initialize conversational components if available
        if CONVERSATIONAL_ENABLED:
            try:
                self.intent_engine = IntentEngine()
                self.document_parser = UniversalDocumentParser()
                self.agent_router = AgentRouter()
                self.conversational_config = ConversationalConfig()
                logger.info("Conversational intelligence enabled")
            except Exception as e:
                logger.warning(f"Could not initialize conversational features: {e}")
                self.intent_engine = None
                self.document_parser = None
                self.agent_router = None
        else:
            self.intent_engine = None
            self.document_parser = None
            self.agent_router = None
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle natural language text messages
        Detects user intent and provides contextual responses
        """
        if not update.message or not update.message.text:
            return
        
        user_id = update.effective_user.id
        message_text = update.message.text
        
        # Skip if it's a command (starts with /)
        if message_text.startswith('/'):
            return
        
        logger.info(f"USER {user_id}: Received message: {message_text}")
        
        # If conversational features are enabled, use intent detection
        if self.intent_engine:
            try:
                # Create conversational session
                conv_session = ConversationalSession(session_manager, user_id)
                conv_session.add_message(message_text, role='user')
                
                # Detect intent
                intent_result = self.intent_engine.detect_intent(message_text)
                intent = intent_result['intent']
                confidence = intent_result['confidence']
                
                logger.info(f"USER {user_id}: Detected intent: {intent} (confidence: {confidence:.2%})")
                
                # Update session with detected intent
                if confidence >= 0.5:
                    conv_session.update_intent(intent, confidence)
                
                # Generate contextual response
                response = self._generate_contextual_response(intent, intent_result, conv_session)
                
                await update.message.reply_text(response, parse_mode="Markdown")
                conv_session.add_message(response, role='bot')
                
            except Exception as e:
                logger.error(f"USER {user_id}: Error in conversational handling: {e}")
                await update.message.reply_text(
                    "I can help you consolidate test results! 📊\n\n"
                    "Just upload your Excel test files and I'll process them."
                )
        else:
            # Fallback: simple response
            await update.message.reply_text(
                "👋 I can help you consolidate test results!\n\n"
                "📤 Send me your Excel test files (Test 1.xlsx, Test 2.xlsx, etc.)\n"
                "Then use /consolidate to process them."
            )
    
    def _generate_contextual_response(self, intent: str, intent_result: dict, 
                                     conv_session: ConversationalSession) -> str:
        """
        Generate context-aware response based on detected intent
        
        Args:
            intent: Detected intent name
            intent_result: Full intent detection result
            conv_session: Conversational session
            
        Returns:
            Response message text
        """
        # Get current session state
        doc_count = conv_session.get_document_count()
        
        if intent == 'test_consolidation':
            if doc_count == 0:
                return (
                    "📊 **Test Consolidation Mode**\n\n"
                    "I'll help you consolidate test results!\n\n"
                    "📤 Send me your Excel files:\n"
                    "• Test 1.xlsx\n"
                    "• Test 2.xlsx\n"
                    "• Test 3.xlsx (and so on)\n\n"
                    "I'll merge them by participant email."
                )
            else:
                return (
                    f"📊 **Test Consolidation in Progress**\n\n"
                    f"✅ You've uploaded {doc_count} file(s)\n\n"
                    f"You can:\n"
                    f"• Upload more test files\n"
                    f"• Use /consolidate to process now"
                )
        
        elif intent == 'invoice_processing':
            return (
                "💰 **Invoice Processing**\n\n"
                "This feature is coming soon! Currently, I specialize in test result consolidation.\n\n"
                "📤 Send me test Excel files to get started."
            )
        
        elif intent == 'image_extraction':
            return (
                "📸 **Image Text Extraction (OCR)**\n\n"
                "This feature is coming soon! Currently, I work with Excel files.\n\n"
                "📤 Send me test Excel files for consolidation."
            )
        
        elif intent == 'table_merge' or intent == 'data_cleaning' or intent == 'report_generation':
            return (
                f"🔧 **{intent.replace('_', ' ').title()}**\n\n"
                f"✅ This feature is now available!\n\n"
                f"📤 Send me your data files (Excel, CSV) and I'll process them.\n"
                f"You can upload multiple files for {intent.replace('_', ' ')}."
            )
        
        elif intent == 'unknown':
            suggestions = intent_result.get('suggestions', [])
            response = "I'm here to help! 🤖\n\n"
            if suggestions:
                response += "\n".join(suggestions)
            else:
                response += (
                    "I can help with:\n"
                    "• Test result consolidation 📊\n"
                    "• Merging Excel files by email\n"
                    "• Creating color-coded reports\n\n"
                    "Just upload your test files to get started!"
                )
            return response
        
        # Default response
        return (
            "I understand you want help with test consolidation! 📊\n\n"
            "Send me your Excel test files and I'll merge them for you."
        )
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /start command — entry point for ConversationHandler"""
        user_id = update.effective_user.id
        
        welcome_text = (
            "✨ <b>MLJ Results Compiler</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Welcome! I consolidate test results from multiple Excel files "
            "into one clean, color-coded report — instantly.\n\n"
            "📋 <b>How it works:</b>\n"
            "1️⃣ Send me your <code>.xlsx</code> test files\n"
            "2️⃣ I merge them by participant email\n"
            "3️⃣ Download your consolidated results\n\n"
            "📤 <b>Send your first file now to get started!</b>\n\n"
            "💡 <i>Tip: Name your files Test 1.xlsx, Test 2.xlsx, etc. for best results</i>"
        )
        
        await update.message.reply_text(welcome_text, parse_mode="HTML")
        logger.info(f"User {user_id} started the bot")
        return SELECTING_FORMAT
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /help command"""
        help_text = (
            "📖 <b>MLJ Results Compiler — Help</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Commands:</b>\n"
            "/start — Start fresh\n"
            "/consolidate — Process uploaded files\n"
            "/help — This help message\n"
            "/cancel — Cancel current operation\n\n"
            "<b>File Requirements:</b>\n"
            "• Format: <code>.xlsx</code> (Excel)\n"
            "• Required columns: Full Name, Email, Score\n"
            "• Naming: Test 1.xlsx, Test 2.xlsx, etc.\n\n"
            "<b>Output:</b>\n"
            "📊 Color-coded Excel with:\n"
            "• All test scores merged by participant\n"
            "• Participation bonus calculated\n"
            "• Final average &amp; Pass/Fail status\n\n"
            "<b>Color Key:</b>\n"
            "⬜ Test 1 · 🟦 Test 2 · 🟨 Test 3 · 🟩 Test 4 · 🟥 Test 5\n\n"
            "📤 <b>Send your .xlsx files to get started!</b>"
        )
        
        await update.effective_message.reply_text(help_text, parse_mode="HTML")
        return SELECTING_FORMAT
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle uploaded documents - collect files without immediate processing"""
        user_id = update.effective_user.id
        
        try:
            document = update.message.document
            logger.info(f"USER {user_id}: Document received: {document.file_name}")
            
            if not document.file_name.lower().endswith('.xlsx'):
                await update.message.reply_text(
                    "❌ <b>Unsupported file type</b>\n\n"
                    "Please send <code>.xlsx</code> Excel files only.",
                    parse_mode="HTML"
                )
                return SELECTING_FORMAT
            
            # Get session and temp directory
            session = session_manager.get_session(user_id)
            temp_dir = Path(session['temp_dir'])
            
            # Download file
            try:
                file = await context.bot.get_file(document.file_id)
                file_path = temp_dir / document.file_name
                await file.download_to_drive(file_path)
                logger.info(f"USER {user_id}: File downloaded to {file_path}")
            except Exception as e:
                logger.error(f"USER {user_id}: Failed to download file: {e}", exc_info=True)
                await update.message.reply_text(
                    f"❌ Failed to download file: {str(e)}"
                )
                return SELECTING_FORMAT
            
            logger.info(f"USER {user_id}: Received file: {document.file_name}")
            logger.info(f"USER {user_id}: Saved to: {file_path}")
            logger.info(f"USER {user_id}: Temp dir now contains: {[f.name for f in temp_dir.glob('*.xlsx')]}")
            
            # Detect test number from filename (Test 1, Test 2, etc.)
            try:
                test_num = self._extract_test_number(document.file_name)
                logger.info(f"USER {user_id}: Extracted test number: {test_num}")
            except Exception as e:
                logger.error(f"USER {user_id}: Error extracting test number: {e}", exc_info=True)
                await update.message.reply_text(
                    f"❌ Error processing filename: {str(e)}"
                )
                return SELECTING_FORMAT
            
            if test_num is None:
                await update.message.reply_text(
                    "⚠️ <b>Could not detect test number</b>\n\n"
                    "Please name your file with a number, e.g.:\n"
                    "• <code>Test 1.xlsx</code>\n"
                    "• <code>Test 2.xlsx</code>\n"
                    "• <code>1.xlsx</code>\n\n"
                    "Rename and resend the file.",
                    parse_mode="HTML"
                )
                return SELECTING_FORMAT
            
            # Add file to session
            try:
                summary = session_manager.add_file(user_id, str(file_path), test_num)
                logger.info(f"USER {user_id}: Added Test {test_num} to session")
            except Exception as e:
                logger.error(f"USER {user_id}: Error adding file to session: {e}", exc_info=True)
                await update.message.reply_text(
                    f"❌ Error processing file: {str(e)}"
                )
                return SELECTING_FORMAT
            
            # Count total files in session
            session = session_manager.get_session(user_id)
            uploaded = session.get('uploaded_files', {})
            file_count = len(uploaded)
            file_list = ', '.join(f'Test {n}' for n in sorted(uploaded.keys()))
            
            # Send clean upload confirmation
            await update.message.reply_text(
                f"✅ <b>Test {test_num}</b> received!\n\n"
                f"📁 Files uploaded: <b>{file_count}</b> ({file_list})\n\n"
                f"📤 Send more files or tap /consolidate when ready.",
                parse_mode="HTML"
            )
            
            return SELECTING_FORMAT
            
        except Exception as e:
            logger.error(f"USER {user_id}: Unexpected error in handle_document: {e}", exc_info=True)
            try:
                await update.message.reply_text(
                    f"❌ Something went wrong processing your file.\n"
                    f"Please try sending it again.",
                    parse_mode="HTML"
                )
            except Exception as reply_error:
                logger.error(f"USER {user_id}: Failed to send error message: {reply_error}")
            return SELECTING_FORMAT
    
    @staticmethod
    def _extract_test_number(filename: str) -> int:
        """
        Extract test number from filename.
        Supports multiple formats:
        - 'Test 1.xlsx', 'test 1.xlsx', 'Test1.xlsx'
        - '1.xlsx', 'result_1.xlsx', 'exam(1).xlsx'
        - Any filename with a number in it
        """
        import re
        
        # Remove extension to focus on the name part
        name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
        
        # Try 1: Look for "Test N" or "test N" format first (preferred)
        match = re.search(r'[Tt]est\s*(\d+)', name_without_ext)
        if match:
            return int(match.group(1))
        
        # Try 2: Look for any number in the filename (if no "Test" prefix)
        # This handles: "1.xlsx", "result_1", "exam(1)", etc.
        match = re.search(r'(\d+)', name_without_ext)
        if match:
            return int(match.group(1))
        
        # No number found
        return None
    
    async def show_format_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Show format selection buttons — Excel only (PDF/DOCX not yet available)"""
        keyboard = [
            [
                InlineKeyboardButton("📊 Download Excel", callback_data='format_xlsx'),
            ],
            [
                InlineKeyboardButton("❌ Cancel", callback_data='format_cancel'),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.effective_message.reply_text(
            "📋 Ready to consolidate! Choose your output:",
            reply_markup=reply_markup
        )
        
        return SELECTING_FORMAT
    
    @staticmethod
    def _generate_preview(consolidated_data: Dict, max_rows: int = 10, validation_report: Dict = None) -> str:
        """Generate a text preview of consolidated results with validation warnings"""
        if not consolidated_data:
            return "❌ No data to preview"
        
        # Get summary stats
        total_participants = len(consolidated_data)
        test_nums = set()
        for data in consolidated_data.values():
            for key in data.keys():
                if key.startswith('test_') and key.endswith('_score'):
                    test_nums.add(int(key.split('_')[1]))
        
        test_nums = sorted(test_nums)
        
        # Build preview text
        preview = f"""
📊 **CONSOLIDATION PREVIEW**

📈 **Summary:**
• Total Participants: {total_participants}
• Tests Consolidated: {', '.join(f'Test {t}' for t in test_nums)}
"""
        
        # Add validation warnings if present
        if validation_report:
            if validation_report.get('missing_participants'):
                preview += f"\n⚠️ **MISSING SCORES:** {len(validation_report['missing_participants'])} participant(s) missing from some tests"
                for item in validation_report['missing_participants'][:3]:
                    preview += f"\n   • {item['name']} - missing in Test {item['missing_in_test']}"
                if len(validation_report['missing_participants']) > 3:
                    preview += f"\n   ... and {len(validation_report['missing_participants']) - 3} more"
            
            if validation_report.get('name_mismatches'):
                preview += f"\n🔴 **NAME MISMATCH:** {len(validation_report['name_mismatches'])} name conflict(s)"
                for item in validation_report['name_mismatches'][:2]:
                    preview += f"\n   • {item['email']}: Test 1='{item['test_1_name']}' vs Test {item['test_num']}='{item['conflicting_name']}'"
            
            if validation_report.get('duplicate_scores'):
                preview += f"\n❓ **IDENTICAL SCORES:** {len(validation_report['duplicate_scores'])} participant(s)"
                for item in validation_report['duplicate_scores'][:3]:
                    preview += f"\n   • {item['name']}: {item['score']} in all tests (possible error?)"
        
        preview += f"\n\n📋 **First {min(max_rows, total_participants)} Records:**\n"
        
        # Add sample rows
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
            preview += f"\n{idx+1}. {name} ({email})\n   {score_str}"
        
        # Show if there are more
        if len(consolidated_data) > max_rows:
            preview += f"\n\n... and {len(consolidated_data) - max_rows} more participants"
        
        preview += "\n\n✅ **Look correct?**"
        return preview
    
    async def show_consolidation_preview(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Show preview of consolidated data before downloading"""
        user_id = update.effective_user.id
        
        # Get or create consolidated data from context
        if 'consolidated_data' not in context.user_data:
            await update.message.reply_text("❌ No consolidation in progress")
            return ConversationHandler.END
        
        consolidated_data = context.user_data['consolidated_data']
        preview = self._generate_preview(consolidated_data)
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Looks Good!", callback_data='preview_confirm'),
                InlineKeyboardButton("❓ Show Full Data", callback_data='preview_full'),
            ],
            [
                InlineKeyboardButton("❌ Cancel", callback_data='preview_cancel'),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            preview,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        return CONFIRMING_PREVIEW
    
    async def handle_preview_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle user action on preview (confirm, show more, or cancel)"""
        query = update.callback_query
        user_id = update.effective_user.id
        await query.answer()
        
        action = query.data.split('_')[1]  # confirm, full, or cancel
        
        if action == 'cancel':
            # Try to delete image message
            try:
                await query.delete_message()
            except:
                await query.edit_message_text("❌ Operation cancelled")
            return ConversationHandler.END
        
        elif action == 'full':
            # Show full data preview
            consolidated_data = context.user_data.get('consolidated_data', {})
            validation_report = context.user_data.get('validation_report')
            processor = context.user_data.get('processor')
            
            # Generate full preview image (all rows)
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
                    except Exception as e:
                        logger.error(f"Error sending full image: {str(e)}")
                        full_preview = self._generate_preview(consolidated_data, max_rows=999, validation_report=validation_report)
                        await query.edit_message_text(full_preview)
                    return CONFIRMING_PREVIEW
            
            # Fallback to text
            full_preview = self._generate_preview(consolidated_data, max_rows=999, validation_report=validation_report)
            await query.edit_message_text(full_preview)
            return CONFIRMING_PREVIEW
        
        elif action == 'confirm':
            # User confirmed, show format selection (Excel only — PDF/DOCX not implemented)
            try:
                await query.delete_message()
            except:
                pass
            
            keyboard = [
                [
                    InlineKeyboardButton("📊 Download Excel", callback_data='format_xlsx'),
                ],
                [
                    InlineKeyboardButton("❌ Cancel", callback_data='format_cancel'),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="📋 Great! Choose your output format:",
                reply_markup=reply_markup
            )
            return SELECTING_OUTPUT_FORMAT
        
        return CONFIRMING_PREVIEW
    
    async def format_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle format selection - consolidate and show preview"""
        query = update.callback_query
        user_id = update.effective_user.id
        await query.answer()
        
        # Get session
        session = session_manager.get_session(user_id)
        uploaded_files = session_manager.get_files_for_consolidation(user_id)
        
        if not uploaded_files:
            await query.edit_message_text(
                "❌ No files found. Please upload files first with /start"
            )
            return ConversationHandler.END
        
        # Safe callback data parsing (BUG 2 fix)
        if query.data == 'format_cancel' or query.data == 'cancel':
            await query.edit_message_text("❌ Operation cancelled. Use /start to begin again.")
            session_manager.clear_session(user_id)
            return ConversationHandler.END
        
        format_choice = query.data.replace('format_', '')  # Extract 'xlsx', 'pdf', or 'docx'
        
        try:
            await query.edit_message_text(
                "⏳ Consolidating your files... please wait."
            )
            
            # Create processor with session files
            input_dir = Path(session['temp_dir'])
            output_dir = Path(tempfile.mkdtemp())
            
            logger.info(f"User {user_id}: Processing files from {input_dir}")
            logger.info(f"Uploaded files dict: {uploaded_files}")
            
            try:
                processor = ExcelProcessor(str(input_dir), str(output_dir))
                logger.info(f"User {user_id}: Created ExcelProcessor")
            except Exception as e:
                logger.error(f"User {user_id}: Failed to create ExcelProcessor: {e}", exc_info=True)
                raise
            
            # Load uploaded files dynamically (detects max test number)
            try:
                loaded = processor.load_all_tests()
                logger.info(f"User {user_id}: Successfully loaded {loaded} test files")
                logger.info(f"Loaded test numbers: {sorted(processor.test_data.keys())}")
                for test_num, data in processor.test_data.items():
                    logger.info(f"  Test {test_num}: {len(data)} participants - {list(data.keys())}")
            except Exception as e:
                logger.error(f"User {user_id}: Failed to load tests: {e}", exc_info=True)
                raise
            
            if loaded == 0:
                logger.error(f"User {user_id}: No valid test files found in {input_dir}")
                # List what's in the directory for debugging
                if input_dir.exists():
                    files_in_dir = list(input_dir.glob("*.xlsx"))
                    logger.error(f"Files in {input_dir}: {[f.name for f in files_in_dir]}")
                
                await query.edit_message_text(
                    "❌ No valid test files found. Please check your files and try again."
                )
                session_manager.clear_session(user_id)
                return ConversationHandler.END
            
            logger.info(f"User {user_id}: Loaded {loaded} test files for consolidation")
            
            # Validate data integrity
            validation_report = processor.validate_data_integrity()
            context.user_data['validation_report'] = validation_report
            
            # Consolidate
            consolidated_data = processor.consolidate_results()
            logger.info(f"User {user_id}: Consolidation returned {len(consolidated_data)} participants")
            if consolidated_data:
                logger.info(f"Consolidated participants: {list(consolidated_data.keys())[:5]}...")  # First 5
                first_email = list(consolidated_data.keys())[0]
                first_data = consolidated_data[first_email]
                logger.info(f"First participant {first_email}: {first_data}")
            
            if not consolidated_data:
                logger.error(f"User {user_id}: Consolidation failed - no data returned")
                logger.error(f"Processor test_data keys: {list(processor.test_data.keys())}")
                for test_num, data in processor.test_data.items():
                    logger.error(f"  Test {test_num}: {len(data)} participants")
                
                await query.edit_message_text(
                    "❌ Failed to consolidate results"
                )
                self.cleanup_session(user_id)
                return ConversationHandler.END
            
            # Store consolidated data and format choice for later use
            context.user_data['consolidated_data'] = consolidated_data
            context.user_data['processor'] = processor
            context.user_data['output_dir'] = str(output_dir)
            context.user_data['format_choice'] = format_choice
            
            # Generate visual preview image
            preview_image_path = processor.generate_preview_image(consolidated_data, max_rows=10)
            if preview_image_path and preview_image_path.exists():
                context.user_data['preview_image_path'] = str(preview_image_path)
                
                # Build validation warnings text
                warnings_text = ""
                if validation_report:
                    if validation_report.get('missing_participants'):
                        warnings_text += f"\n⚠️ Missing scores: {len(validation_report['missing_participants'])} participant(s)"
                    if validation_report.get('name_mismatches'):
                        warnings_text += f"\n🔴 Name conflicts: {len(validation_report['name_mismatches'])}"
                    if validation_report.get('duplicate_scores'):
                        warnings_text += f"\n❓ Identical scores: {len(validation_report['duplicate_scores'])} participant(s)"
                
                caption = f"📊 Consolidation Preview \u2014 {len(consolidated_data)} participants"
                if warnings_text:
                    caption += warnings_text
                caption += "\n\nTap a button below to continue."
                
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Looks Good!", callback_data='preview_confirm'),
                        InlineKeyboardButton("🔍 Full Data", callback_data='preview_full'),
                    ],
                    [
                        InlineKeyboardButton("❌ Cancel", callback_data='preview_cancel'),
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Send photo with buttons
                with open(preview_image_path, 'rb') as photo_file:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=photo_file,
                        caption=caption,
                        reply_markup=reply_markup
                    )
                
                # Try to delete the old message if possible
                try:
                    await query.delete_message()
                except:
                    # If deletion fails, that's fine - message will just stay
                    pass
            else:
                # Fallback to text preview if image generation failed
                logger.warning("Preview image generation failed, falling back to text preview")
                preview = self._generate_preview(consolidated_data, validation_report=validation_report)
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Looks Good!", callback_data='preview_confirm'),
                        InlineKeyboardButton("🔍 Full Data", callback_data='preview_full'),
                    ],
                    [
                        InlineKeyboardButton("❌ Cancel", callback_data='preview_cancel'),
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    preview,
                    reply_markup=reply_markup
                )
            
            return CONFIRMING_PREVIEW
            
        except Exception as e:
            logger.error(f"Error processing files for user {user_id}: {str(e)}")
            await query.edit_message_text(
                f"❌ Error: {str(e)}\n\nPlease try again or contact support."
            )
            self.cleanup_session(user_id)
            return ConversationHandler.END
    
    async def format_confirmed(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle format selection after preview is confirmed"""
        query = update.callback_query
        user_id = update.effective_user.id
        await query.answer()
        
        # Safe callback data parsing (BUG 2 fix)
        if query.data == 'format_cancel' or query.data == 'cancel':
            await query.edit_message_text("❌ Operation cancelled. Use /start to begin again.")
            self.cleanup_session(user_id)
            return ConversationHandler.END
        
        format_choice = query.data.replace('format_', '')  # Extract 'xlsx'
        
        try:
            consolidated_data = context.user_data.get('consolidated_data', {})
            processor = context.user_data.get('processor')
            output_dir = Path(context.user_data.get('output_dir', tempfile.gettempdir()))
            
            if not consolidated_data or not processor:
                await query.edit_message_text("❌ Session expired. Please use /start to begin again.")
                return ConversationHandler.END
            
            # Only Excel is currently supported
            if format_choice not in ('xlsx',):
                await query.edit_message_text(
                    f"⚠️ {format_choice.upper()} export is not yet available.\n"
                    f"Generating Excel instead..."
                )
                format_choice = 'xlsx'
            
            await query.edit_message_text("⏳ Generating your report...")
            
            # Generate Excel file
            output_file = output_dir / 'Consolidated_Results.xlsx'
            success = processor.save_consolidated_file(consolidated_data, output_file.name)
            
            if not success or not output_file.exists():
                await query.edit_message_text(
                    "❌ Failed to generate the file. Please try again with /start."
                )
                self.cleanup_session(user_id)
                return ConversationHandler.END
            
            # Count stats for the celebration message
            test_nums = set()
            for data in consolidated_data.values():
                for key in data.keys():
                    if key.startswith('test_') and key.endswith('_score'):
                        test_nums.add(int(key.split('_')[1]))
            
            # Send the file
            with open(output_file, 'rb') as f:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=f,
                    filename=output_file.name
                )
            
            # UX 4: Success celebration
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=(
                    "✅ <b>Report delivered!</b>\n"
                    "━━━━━━━━━━━━━━━━━━\n\n"
                    f"👥 <b>{len(consolidated_data)}</b> participants\n"
                    f"📝 <b>{len(test_nums)}</b> tests merged ({', '.join(f'Test {t}' for t in sorted(test_nums))})\n"
                    f"📊 Format: Excel (color-coded)\n\n"
                    f"🔄 Send more files anytime or tap /start to begin a new session."
                ),
                parse_mode="HTML"
            )
            
            logger.info(f"User {user_id}: Delivered consolidated results ({len(consolidated_data)} participants, {len(test_nums)} tests)")
            
            self.cleanup_session(user_id)
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error generating file for user {user_id}: {str(e)}", exc_info=True)
            await query.edit_message_text(
                "❌ Something went wrong generating your report.\n"
                "Please try again with /start."
            )
            self.cleanup_session(user_id)
            return ConversationHandler.END
    
    async def consolidate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /consolidate command - process all uploaded files on demand"""
        user_id = update.effective_user.id
        
        # Get user session
        session = session_manager.get_session(user_id)
        uploaded_files = session_manager.get_files_for_consolidation(user_id)
        
        if not uploaded_files:
            await update.message.reply_text(
                "📁 No files uploaded yet.\n"
                "Please send at least one test file to get started."
            )
            return SELECTING_FORMAT
        
        # Show format selection
        return await self.show_format_selection(update, context)
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /cancel command"""
        user_id = update.effective_user.id
        self.cleanup_session(user_id)
        
        await update.effective_message.reply_text(
            "❌ Session cancelled.\n\n"
            "Tap /start to begin a new session."
        )
        return ConversationHandler.END
    
    @staticmethod
    def cleanup_session(user_id):
        """Clean up temporary files for a user"""
        session_manager.clear_session(user_id)

def build_application(token: str) -> Application:
    application = Application.builder().token(token).job_queue(None).build()
    handler = TelegramBotHandler(token)

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", handler.start),
            MessageHandler(filters.Document.FileExtension("xlsx"), handler.handle_document),
        ],
        states={
            SELECTING_FORMAT: [
                MessageHandler(filters.Document.FileExtension("xlsx"), handler.handle_document),
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
    
    # Standalone handlers for when user is NOT in a conversation
    application.add_handler(CommandHandler("help", handler.help_command))
    application.add_handler(CommandHandler("start", handler.start))
    
    # Add text message handler for conversational mode (outside conversation flow)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handler.handle_message)
    )

    return application


def main():
    """Start the Telegram bot using long polling (local/dev)."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')

    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        raise ValueError("Please set TELEGRAM_BOT_TOKEN in .env file")

    application = build_application(token)

    logger.info("Starting MLJ Results Compiler Telegram Bot (polling)")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
