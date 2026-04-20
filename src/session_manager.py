"""
Session Management Agent for MLJ Bot
Tracks user sessions, uploaded files, and consolidation workflow state
Enhanced with conversational intelligence and multi-format document support
"""

import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages user sessions and file tracking"""
    
    def __init__(self):
        self.sessions = {}  # {user_id: session_data}
    
    def get_session(self, user_id: int) -> Dict:
        """Get or create user session"""
        if user_id not in self.sessions:
            self.sessions[user_id] = {
                'user_id': user_id,
                'created_at': datetime.now(),
                'uploaded_files': {},  # {test_num: file_path} - legacy format
                'temp_dir': tempfile.mkdtemp(),
                'state': 'waiting_for_files',  # waiting_for_files, ready_to_consolidate
                'messages': [],
                # NEW: Conversational features
                'conversation_history': [],  # List of {role, message, timestamp}
                'detected_intent': None,
                'intent_confidence': 0.0,
                'collected_documents': [],  # Enhanced file tracking with metadata
                'clarification_needed': [],
                'processing_context': {
                    'merge_strategy': None,
                    'output_format': None,
                    'custom_columns': [],
                    'filters': {},
                    'detected_schema': None
                },
                'workflow_state': 'initial'  # initial → collecting → clarifying → processing → complete
            }
            logger.info(f"Created new session for user {user_id}")
        
        return self.sessions[user_id]
    
    def add_file(self, user_id: int, file_path: str, test_num: int) -> Dict:
        """Add a file to user session"""
        session = self.get_session(user_id)
        
        # If file for this test already exists, replace it
        if test_num in session['uploaded_files']:
            old_path = session['uploaded_files'][test_num]
            try:
                Path(old_path).unlink()
                logger.info(f"Replaced Test {test_num} file for user {user_id}")
            except Exception as e:
                logger.warning(f"Could not delete old file: {e}")
        
        session['uploaded_files'][test_num] = file_path
        session['messages'].append(f"[OK] Test {test_num} file received")
        
        # Update session state based on files
        session['state'] = self.determine_state(session)
        
        return self.get_session_summary(user_id)
    
    def get_session_summary(self, user_id: int) -> Dict:
        """Get session summary for user feedback"""
        session = self.get_session(user_id)
        uploaded = sorted(session['uploaded_files'].keys())
        
        return {
            'tests_uploaded': uploaded,
            'count': len(uploaded),
            'messages': session['messages'],
            'can_consolidate': len(uploaded) > 0,  # Can consolidate with any test file
            'state': self.determine_state(session)
        }
    
    def determine_state(self, session: Dict) -> str:
        """Agentic reasoning: Determine what state session should be in"""
        uploaded = session['uploaded_files']
        
        # Decision tree for state
        if not uploaded:
            return 'waiting_for_files'  # Must have at least one file
        elif len(uploaded) == 1:
            return 'can_consolidate_alone'  # Can process single test
        else:
            return 'ready_to_consolidate'  # Have multiple tests
    
    def get_files_for_consolidation(self, user_id: int) -> Dict[int, str]:
        """Get uploaded files ready for consolidation"""
        session = self.get_session(user_id)
        return session['uploaded_files'].copy()
    
    def clear_session(self, user_id: int) -> bool:
        """Clear session and cleanup temp files"""
        if user_id not in self.sessions:
            return False
        
        session = self.sessions[user_id]
        try:
            if Path(session['temp_dir']).exists():
                shutil.rmtree(session['temp_dir'])
            del self.sessions[user_id]
            logger.info(f"Cleared session for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error clearing session: {e}")
            return False
    
    def format_status_message(self, user_id: int) -> str:
        """Format session status as Telegram message"""
        summary = self.get_session_summary(user_id)
        tests = summary['tests_uploaded']
        state = summary['state']
        
        msg = "[FILE STATUS]\n\n"
        msg += f"Uploaded: {len(tests)} file(s)\n"
        
        if tests:
            msg += "[OK] Tests: " + ", ".join([f"Test {t}" for t in tests]) + "\n\n"
        else:
            msg += "No files uploaded yet\n\n"
        
        # State-based guidance
        if state == 'waiting_for_files':
            msg += "[REQUIRED] Upload at least one test file to get started\n"
            msg += "Send any Test file (Test 1, 2, 3, etc.)"
        elif state == 'can_consolidate_alone':
            msg += "[READY] You can:\n"
            msg += f"- Send more tests for comparison\n"
            msg += "- Or press /consolidate to process uploaded test(s)"
        elif state == 'ready_to_consolidate':
            msg += f"[READY] Ready to consolidate!\n"
            msg += f"Press /consolidate to merge all {len(tests)} tests"
        
        return msg


class ConversationalSession:
    """Enhanced session manager with conversation intelligence"""
    
    def __init__(self, session_manager: SessionManager, user_id: int):
        """
        Initialize conversational session wrapper
        
        Args:
            session_manager: Base SessionManager instance
            user_id: User ID
        """
        self.session_manager = session_manager
        self.user_id = user_id
        self.session = session_manager.get_session(user_id)
    
    def add_message(self, message: str, role: str = 'user'):
        """
        Track conversation with context
        
        Args:
            message: Message text
            role: 'user' or 'bot' or 'system'
        """
        self.session['conversation_history'].append({
            'role': role,
            'message': message,
            'timestamp': datetime.now(),
            'intent': self.session.get('detected_intent')
        })
        logger.debug(f"Added message to conversation history (role: {role})")
    
    def update_intent(self, intent: str, confidence: float):
        """
        Update detected intent with confidence tracking
        
        Args:
            intent: Detected intent name
            confidence: Confidence score (0-1)
        """
        self.session['detected_intent'] = intent
        self.session['intent_confidence'] = confidence
        self.add_message(f"Intent detected: {intent} ({confidence:.2%})", role='system')
        logger.info(f"Updated intent for user {self.user_id}: {intent} ({confidence:.2%})")
    
    def add_document(self, file_path: str, file_info: Dict[str, Any]):
        """
        Enhanced file tracking with metadata
        
        Args:
            file_path: Path to uploaded file
            file_info: File metadata from document parser
        """
        self.session['collected_documents'].append({
            'path': file_path,
            'format': file_info.get('format'),
            'type': file_info.get('type'),
            'size': file_info.get('size'),
            'name': file_info.get('name'),
            'parsed_data': None,  # Will be populated by parser
            'schema': None,
            'uploaded_at': datetime.now()
        })
        logger.info(f"Added document to session: {file_info.get('name')}")
    
    def get_document_count(self) -> int:
        """Get number of uploaded documents"""
        return len(self.session.get('collected_documents', []))
    
    def get_documents(self) -> List[Dict[str, Any]]:
        """Get all uploaded documents"""
        return self.session.get('collected_documents', [])
    
    def generate_clarification(self) -> Optional[str]:
        """
        Generate intelligent clarification questions
        
        Returns:
            Clarification question or None
        """
        intent = self.session.get('detected_intent')
        documents = self.session.get('collected_documents', [])
        
        if intent == 'test_consolidation':
            if not documents:
                return "Please upload your test Excel files to get started."
            elif len(documents) < 2:
                return "You can upload more test files or use /consolidate to process."
        
        return None
    
    def infer_user_goal(self) -> Dict[str, Any]:
        """
        Use conversation history to infer what user wants
        
        Returns:
            Dictionary with inferred goals and context
        """
        history = self.session.get('conversation_history', [])
        intent = self.session.get('detected_intent')
        documents = self.session.get('collected_documents', [])
        
        return {
            'intent': intent,
            'confidence': self.session.get('intent_confidence', 0.0),
            'has_files': len(documents) > 0,
            'file_count': len(documents),
            'message_count': len(history),
            'workflow_state': self.session.get('workflow_state', 'initial')
        }
    
    def get_conversation_context(self, limit: int = 5) -> str:
        """
        Get recent conversation for context-aware responses
        
        Args:
            limit: Number of recent messages to include
            
        Returns:
            Formatted conversation context
        """
        history = self.session.get('conversation_history', [])
        recent = history[-limit:] if len(history) > limit else history
        
        return "\n".join([f"{m['role']}: {m['message']}" for m in recent])
    
    def update_workflow_state(self, state: str):
        """
        Update workflow state
        
        Args:
            state: New state (initial, collecting, clarifying, processing, complete)
        """
        self.session['workflow_state'] = state
        logger.info(f"Workflow state updated to: {state}")


class WorkflowAgent:
    """Agent for orchestrating consolidation workflow"""
    
    @staticmethod
    def should_consolidate(session: Dict) -> bool:
        """Agentic reasoning: Should consolidation happen?"""
        # Consolidation is possible if:
        # 1. User explicitly requests it (handled by command)
        # 2. At least one test file is uploaded
        return len(session['uploaded_files']) > 0
    
    @staticmethod
    def get_next_action(session: Dict) -> str:
        """Agentic reasoning: What should bot do next?"""
        uploaded = session['uploaded_files']
        
        if not uploaded:
            return "ask_for_files"
        elif len(uploaded) < 5:
            return "offer_consolidate_or_continue"  # Can accept more or consolidate
        else:
            return "ready_consolidate"
    
    @staticmethod
    def format_suggestion(action: str) -> str:
        """Format bot suggestion based on next action"""
        suggestions = {
            "ask_for_files": "[INFO] Send test file(s) to get started",
            "offer_consolidate_or_continue": "[INFO] You can send more tests or press /consolidate now",
            "ready_consolidate": "[OK] Multiple tests uploaded! Press /consolidate to process"
        }
        return suggestions.get(action, "Ready for next step")
