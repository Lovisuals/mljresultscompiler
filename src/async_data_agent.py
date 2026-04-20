# -*- coding: utf-8 -*-
"""
Async Data Agent - Non-blocking data transformations
Wraps DataAgent with proper async/await for concurrent data operations.
Prevents event loop blocking from pandas operations and file I/O.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

logger = logging.getLogger(__name__)

# Thread pool for CPU-bound pandas operations
_executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="data_async_")


class AsyncDataAgent:
    """
    Non-blocking wrapper for data operations.
    
    Converts all blocking pandas/data operations to async, enabling
    concurrent data transformations without blocking the event loop.
    """
    
    def __init__(self, data_agent=None):
        """
        Initialize async data agent wrapper.
        
        Args:
            data_agent: The synchronous DataAgent instance to wrap
        """
        self.agent = data_agent
        self.operation_timeout = 15.0  # Operation timeout in seconds
        self.operation_semaphore = asyncio.Semaphore(4)  # Max 4 concurrent data ops
        
        logger.info("✓ AsyncDataAgent initialized")
    
    async def execute_async(
        self,
        action: str,
        data: pd.DataFrame,
        params: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> Dict:
        """
        Execute data operation asynchronously (non-blocking).
        
        Args:
            action: Action name (e.g., "add_random_scores")
            data: DataFrame to manipulate
            params: Action parameters
            timeout: Operation timeout
            
        Returns:
            Dict with success status, modified data, and message
            
        Raises:
            asyncio.TimeoutError: If operation exceeds timeout
        """
        if not self.agent:
            return {
                "success": False,
                "error": "Data agent not initialized",
                "data": data
            }
        
        timeout = timeout or self.operation_timeout
        
        # Semaphore ensures we don't overwhelm with concurrent operations
        async with self.operation_semaphore:
            try:
                result = await asyncio.wait_for(
                    self._run_execute(action, data, params),
                    timeout=timeout
                )
                return result
            except asyncio.TimeoutError:
                logger.warning(f"Data operation '{action}' timeout after {timeout}s")
                return {
                    "success": False,
                    "error": f"Operation timeout after {timeout}s",
                    "data": data
                }
            except Exception as e:
                logger.error(f"Data operation '{action}' failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "data": data
                }
    
    async def _run_execute(
        self,
        action: str,
        data: pd.DataFrame,
        params: Dict[str, Any]
    ) -> Dict:
        """Run blocking execute in executor"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self.agent.execute,
            action,
            data,
            params
        )
    
    async def batch_execute_async(
        self,
        operations: List[Dict[str, Any]],
        data: pd.DataFrame,
        timeout: Optional[float] = None
    ) -> Dict:
        """
        Execute multiple data operations sequentially on same data.
        
        Args:
            operations: List of {"action": str, "params": dict} dicts
            data: Initial DataFrame
            timeout: Per-operation timeout
            
        Returns:
            Final result with modified data and operation log
        """
        current_data = data
        operation_log = []
        
        for i, op in enumerate(operations):
            action = op.get("action")
            params = op.get("params", {})
            
            result = await self.execute_async(action, current_data, params, timeout)
            
            operation_log.append({
                "step": i + 1,
                "action": action,
                "success": result.get("success", False),
                "message": result.get("message", ""),
                "error": result.get("error")
            })
            
            if result.get("success", False):
                current_data = result.get("data", current_data)
            else:
                logger.warning(f"Operation {action} failed: {result.get('error')}")
                # Continue with current data rather than aborting
        
        return {
            "success": len([op for op in operation_log if op.get("success")]) == len(operations),
            "data": current_data,
            "operations": operation_log,
            "total_operations": len(operations)
        }
    
    async def parallel_execute_async(
        self,
        operations: List[Dict[str, Any]],
        data: pd.DataFrame,
        timeout: Optional[float] = None
    ) -> Dict:
        """
        Execute multiple independent data operations concurrently.
        
        Use this when operations are independent and don't rely on
        each other's results. Results are returned but not chained.
        
        Args:
            operations: List of {"action": str, "params": dict} dicts
            data: DataFrame to apply operations to
            timeout: Per-operation timeout
            
        Returns:
            Dict with results from all operations
        """
        tasks = [
            self.execute_async(
                op.get("action"),
                data,
                op.get("params", {}),
                timeout
            )
            for op in operations
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        return {
            "success": all(r.get("success", False) for r in results),
            "operations": len(operations),
            "results": results
        }


# Global async data agent instance
_async_data_agent: Optional[AsyncDataAgent] = None


def get_async_data_agent() -> AsyncDataAgent:
    """Get or create global async data agent"""
    global _async_data_agent
    if _async_data_agent is None:
        # Import here to avoid circular imports
        from src.data_agent import get_data_agent
        agent = get_data_agent()
        _async_data_agent = AsyncDataAgent(agent)
    return _async_data_agent


async def initialize_async_data_agent():
    """Initialize async data agent"""
    global _async_data_agent
    _async_data_agent = get_async_data_agent()
    logger.info("✓ Async data agent ready")


async def shutdown_async_data_agent():
    """Shutdown async data agent and cleanup executor"""
    global _async_data_agent
    _executor.shutdown(wait=True)
    _async_data_agent = None
    logger.info("✓ Async data agent shutdown")
