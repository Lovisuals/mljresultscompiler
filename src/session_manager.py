import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)

class SessionManager:

    def __init__(self):
        self.sessions = {}

    def get_session(self, user_id: int) -> Dict:
        if user_id not in self.sessions:
            self.sessions[user_id] = {
                'user_id': user_id,
                'created_at': datetime.now(),
                'uploaded_files': {},
                'temp_dir': tempfile.mkdtemp(),
                'status': 'waiting_for_files',
                'messages': [],
                'conversation_history': [],
                'detected_intent': None,
                'intent_confidence': 0.0,
                'collected_documents': [],
                'extracted_entities': [],
                'agent_context': {
                    'current_task': None,
                    'last_action': None,
                    'action_history': [],
                    'task_metadata': {},
                    'error_count': None
                },
                'workflow_state': 'initial'
            }
            logger.info(f"Created new session for user {user_id}")
        return self.sessions[user_id]

    def add_file(self, user_id: int, file_path: str, test_num: int) -> Dict:
        session = self.get_session(user_id)
        if test_num in session['uploaded_files']:
            old_path = session['uploaded_files'][test_num]
            try:
                Path(old_path).unlink()
                logger.info(f"Replaced Test {test_num} file for user {user_id}")
            except Exception as e:
                logger.warning(f"Could not delete old file: {e}")
        session['uploaded_files'][test_num] = file_path
        session['messages'].append(f"[OK] Test {test_num} file received")
        session['state'] = self.determine_state(session)
        return self.get_session_summary(user_id)

    def get_session_summary(self, user_id: int) -> Dict:
        session = self.get_session(user_id)
        uploaded = sorted(session['uploaded_files'].keys())
        return {
            'tests_uploaded': uploaded,
            'file_count': len(uploaded),
            'messages': session['messages'],
            'has_files': len(uploaded) > 0,
            'state': self.determine_state(session)
        }

    def determine_state(self, session: Dict) -> str:
        uploaded = session['uploaded_files']
        if not uploaded:
            return 'waiting_for_files'
        elif len(uploaded) == 1:
            return 'can_consolidate_alone'
        else:
            return 'ready_to_consolidate'

    def get_files_for_consolidation(self, user_id: int) -> Dict[int, str]:
        session = self.get_session(user_id)
        return session['uploaded_files'].copy()

    def clear_session(self, user_id: int) -> bool:
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
        summary = self.get_session_summary(user_id)
        tests = summary['tests_uploaded']
        state = summary['state']
        msg = "[FILE STATUS]\n\n"
        msg += f"Uploaded: {len(tests)} file(s)\n"
        if tests:
            msg += "[OK] Tests: " + ", ".join([f"Test {t}" for t in tests]) + "\n\n"
        else:
            msg += "No files uploaded yet\n\n"
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
    def __init__(self, session_manager: SessionManager, user_id: int):
        self.session_manager = session_manager
        self.user_id = user_id
        self.session = session_manager.get_session(user_id)

    def add_message(self, message: str, role: str = 'user'):
        self.session['conversation_history'].append({
            'role': role,
            'message': message,
            'timestamp': datetime.now(),
            'intent': self.session.get('detected_intent')
        })
        logger.debug(f"Added message to conversation history (role: {role})")

    def update_intent(self, intent: str, confidence: float):
        self.session['detected_intent'] = intent
        self.session['intent_confidence'] = confidence
        self.add_message(f"Intent detected: {intent} ({confidence:.2%})", role='system')
        logger.info(f"Updated intent for user {self.user_id}: {intent} ({confidence:.2%})")

    def add_document(self, file_path: str, file_info: Dict[str, Any]):
        self.session['collected_documents'].append({
            'path': file_path,
            'format': file_info.get('format'),
            'type': file_info.get('type'),
            'size': file_info.get('size'),
            'name': file_info.get('name'),
            'metadata': None,
            'ocr_results': None,
            'created_at': datetime.now()
        })
        logger.info(f"Added document to session: {file_info.get('name')}")

    def get_document_count(self) -> int:
        return len(self.session.get('collected_documents', []))

    def get_documents(self) -> List[Dict[str, Any]]:
        return self.session.get('collected_documents', [])

    def generate_clarification(self) -> Optional[str]:
        intent = self.session.get('detected_intent')
        documents = self.session.get('collected_documents', [])
        if intent == 'test_consolidation':
            if not documents:
                return "Please upload your test Excel files to get started."
            elif len(documents) < 2:
                return "You can upload more test files or use /consolidate to process."
        return None

    def infer_user_goal(self) -> Dict[str, Any]:
        history = self.session.get('conversation_history', [])
        intent = self.session.get('detected_intent')
        documents = self.session.get('collected_documents', [])
        return {
            'intent': intent,
            'confidence': self.session.get('intent_confidence', 0.0),
            'has_files': len(documents) > 0,
            'file_count': len(documents),
            'history_count': len(history),
            'workflow_state': self.session.get('workflow_state', 'initial')
        }

    def get_conversation_context(self, limit: int = 5) -> str:
        history = self.session.get('conversation_history', [])
        recent = history[-limit:] if len(history) > limit else history
        return "\n".join([f"{m['role']}: {m['message']}" for m in recent])

    def update_workflow_state(self, state: str):
        self.session['workflow_state'] = state
        logger.info(f"Workflow state updated to: {state}")

class WorkflowAgent:
    @staticmethod
    def should_consolidate(session: Dict) -> bool:
        return len(session['uploaded_files']) > 0

    @staticmethod
    def get_next_action(session: Dict) -> str:
        uploaded = session['uploaded_files']
        if not uploaded:
            return "ask_for_files"
        elif len(uploaded) < 5:
            return "offer_consolidate_or_continue"
        else:
            return "ready_consolidate"

    @staticmethod
    def format_suggestion(action: str) -> str:
        suggestions = {
            'ask_for_files': "[INFO] Send test file(s) to get started",
            'offer_consolidate_or_continue': "[INFO] You can send more tests or press /consolidate now",
            'ready_consolidate': "[OK] Multiple tests uploaded! Press /consolidate to process"
        }
        return suggestions.get(action, "Ready for next step")
