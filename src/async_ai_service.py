# -*- coding: utf-8 -*-
"""
Async AI Service - Non-blocking AI operations
Wraps AI assistant with proper async/await for concurrent request handling.
Prevents event loop blocking from Groq API calls, data operations, and file I/O.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from functools import wraps
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Thread pool for CPU-bound work and blocking I/O
_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="ai_async_")


def run_in_executor(func):
    """Decorator to run blocking function in thread pool executor"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, lambda: func(*args, **kwargs))
    return async_wrapper


class AsyncAIService:
    """
    Non-blocking wrapper for AI operations.
    
    Converts all blocking AI calls to async, preventing event loop stalls.
    Enables concurrent request handling with proper timeout protection.
    """
    
    def __init__(self, ai_assistant=None):
        """
        Initialize async AI service wrapper.
        
        Args:
            ai_assistant: The synchronous AugmentedAssistant instance to wrap
        """
        self.ai = ai_assistant
        self.call_timeout = 30.0  # API call timeout in seconds
        self.request_semaphore = asyncio.Semaphore(10)  # Max 10 concurrent AI requests
        
        logger.info("✓ AsyncAIService initialized")
    
    async def analyze_message_async(
        self,
        message: str,
        session_id: Optional[str] = None,
        context: Optional[Dict] = None,
        timeout: Optional[float] = None
    ) -> Dict:
        """
        Analyze message asynchronously (non-blocking).
        
        Args:
            message: User message to analyze
            session_id: Session context ID
            context: Additional session context
            timeout: Request timeout (defaults to 30s)
            
        Returns:
            Analysis result dict with response, intent, action
            
        Raises:
            asyncio.TimeoutError: If request exceeds timeout
        """
        if not self.ai:
            return {
                "response": "AI service not available",
                "intent": "unknown",
                "action": None,
                "timestamp": datetime.now().isoformat(),
                "augmented": False,
                "error": "AI assistant not initialized"
            }
        
        timeout = timeout or self.call_timeout
        
        # Semaphore ensures we don't overwhelm the AI service with concurrent requests
        async with self.request_semaphore:
            try:
                # Run blocking AI call in thread pool
                result = await asyncio.wait_for(
                    self._run_analyze_message(message, session_id, context),
                    timeout=timeout
                )
                return result
            except asyncio.TimeoutError:
                logger.warning(f"AI request timeout after {timeout}s for message: {message[:50]}")
                return {
                    "response": "Response timeout - try again",
                    "intent": "unknown",
                    "action": None,
                    "timestamp": datetime.now().isoformat(),
                    "augmented": False,
                    "error": "Request timeout"
                }
            except Exception as e:
                logger.error(f"AI request failed: {e}")
                return {
                    "response": "Error processing request - try again",
                    "intent": "unknown",
                    "action": None,
                    "timestamp": datetime.now().isoformat(),
                    "augmented": False,
                    "error": str(e)
                }
    
    async def _run_analyze_message(
        self,
        message: str,
        session_id: Optional[str],
        context: Optional[Dict]
    ) -> Dict:
        """Run blocking analyze_message in executor"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self.ai.analyze_message,
            message,
            session_id,
            context
        )
    
    async def generate_response_async(
        self,
        prompt: str,
        mode: str = "consolidation",
        timeout: Optional[float] = None
    ) -> str:
        """
        Generate LLM response asynchronously.
        
        Args:
            prompt: Prompt text
            mode: Response mode (consolidation, cold_email, etc.)
            timeout: Request timeout
            
        Returns:
            Generated response text
        """
        if not self.ai or not self.ai.llm_enabled:
            return "AI not available"
        
        timeout = timeout or self.call_timeout
        
        async with self.request_semaphore:
            try:
                result = await asyncio.wait_for(
                    self._run_generate_response(prompt, mode),
                    timeout=timeout
                )
                return result
            except asyncio.TimeoutError:
                logger.warning(f"LLM response timeout after {timeout}s")
                return "Response timeout - please try again"
            except Exception as e:
                logger.error(f"Response generation failed: {e}")
                return f"Error: {str(e)}"
    
    async def _run_generate_response(self, prompt: str, mode: str) -> str:
        """Run blocking LLM call in executor"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self.ai._generate_response,
            prompt,
            mode
        )
    
    async def batch_analyze_messages_async(
        self,
        messages: List[str],
        session_id: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> List[Dict]:
        """
        Analyze multiple messages concurrently (up to semaphore limit).
        
        Args:
            messages: List of messages to analyze
            session_id: Session context
            timeout: Per-request timeout
            
        Returns:
            List of analysis results in same order as input
        """
        tasks = [
            self.analyze_message_async(msg, session_id, timeout=timeout)
            for msg in messages
        ]
        return await asyncio.gather(*tasks, return_exceptions=False)


# Global async AI service instance
_async_ai_service: Optional[AsyncAIService] = None


def get_async_ai_service() -> AsyncAIService:
    """Get or create global async AI service"""
    global _async_ai_service
    if _async_ai_service is None:
        # Import here to avoid circular imports
        from src.ai_assistant import get_assistant
        ai = get_assistant()
        _async_ai_service = AsyncAIService(ai)
    return _async_ai_service


async def initialize_async_ai():
    """Initialize async AI service"""
    global _async_ai_service
    _async_ai_service = get_async_ai_service()
    logger.info("✓ Async AI service ready")


async def shutdown_async_ai():
    """Shutdown async AI service and cleanup executor"""
    global _async_ai_service
    _executor.shutdown(wait=True)
    _async_ai_service = None
    logger.info("✓ Async AI service shutdown")
