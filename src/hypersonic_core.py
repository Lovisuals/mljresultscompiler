"""
Universal Hypersonic Document Processing Core
High-performance, async-first, lightweight engine
Integrates all capabilities: browsing, APIs, learning, multi-platform
"""

import asyncio
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import logging

from src.platform_adapter import PlatformMessage, PlatformResponse, platform_bridge
from src.data_source_manager import DataSource, DataRecord, data_source_manager
from src.document_learning_engine import DocumentFormat, learning_engine

logger = logging.getLogger(__name__)


@dataclass
class ProcessingTask:
    """Unified processing task"""
    task_id: str
    task_type: str  # 'consolidation', 'merge', 'extract', 'transform', etc.
    status: str = 'pending'  # pending, processing, completed, failed
    priority: int = 1  # 1-10, higher = more urgent
    
    # Input sources
    input_sources: List[Union[str, DataSource]] = field(default_factory=list)  # URLs, files, APIs
    input_data: List[DataRecord] = field(default_factory=list)
    
    # Processing config
    config: Dict[str, Any] = field(default_factory=dict)
    learned_format: Optional[DocumentFormat] = None
    
    # Output
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time_ms: float = 0.0
    
    # Platform integration
    platform_message: Optional[PlatformMessage] = None
    user_id: Optional[str] = None


class HypersonicCore:
    """Universal document processing engine"""
    
    def __init__(self, max_workers: int = 16, cache_size: int = 1000):
        self.max_workers = max_workers
        self.cache_size = cache_size
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.tasks: Dict[str, ProcessingTask] = {}
        self.cache: Dict[str, Any] = {}
        self.worker_pool: List[asyncio.Task] = []
        self.performance_stats = {
            'tasks_completed': 0,
            'total_processing_ms': 0.0,
            'cache_hits': 0,
            'cache_misses': 0,
        }
    
    async def initialize(self):
        """Initialize the core engine"""
        logger.info(f"Initializing HypersonicCore with {self.max_workers} workers")
        
        # Start worker pool
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker_loop(i))
            self.worker_pool.append(worker)
        
        # Connect data source manager
        await data_source_manager.connect() if hasattr(data_source_manager, 'connect') else None
        
        logger.info("HypersonicCore ready")
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down HypersonicCore")
        
        # Cancel worker tasks
        for worker in self.worker_pool:
            worker.cancel()
        
        # Wait for cleanup
        await asyncio.gather(*self.worker_pool, return_exceptions=True)
        
        # Close data sources
        await data_source_manager.cleanup()
    
    async def submit_task(self, task: ProcessingTask) -> str:
        """Submit a new processing task"""
        self.tasks[task.task_id] = task
        await self.task_queue.put(task)
        logger.info(f"Submitted task {task.task_id}: {task.task_type}")
        return task.task_id
    
    async def get_task_status(self, task_id: str) -> Optional[ProcessingTask]:
        """Get current task status"""
        return self.tasks.get(task_id)
    
    async def _worker_loop(self, worker_id: int):
        """Worker process loop"""
        logger.info(f"Worker {worker_id} started")
        
        while True:
            try:
                # Get task with timeout
                task = await asyncio.wait_for(self.task_queue.get(), timeout=60)
                
                logger.debug(f"Worker {worker_id} processing {task.task_id}")
                await self._process_task(task)
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
    
    async def _process_task(self, task: ProcessingTask):
        """Process a single task"""
        start_time = datetime.now()
        task.status = 'processing'
        task.started_at = start_time
        
        try:
            # Route based on task type
            if task.task_type == 'consolidation':
                await self._handle_consolidation(task)
            elif task.task_type == 'merge':
                await self._handle_merge(task)
            elif task.task_type == 'extract':
                await self._handle_extraction(task)
            elif task.task_type == 'fetch_remote':
                await self._handle_remote_fetch(task)
            elif task.task_type == 'transform':
                await self._handle_transform(task)
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")
            
            task.status = 'completed'
            
        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}")
            task.status = 'failed'
            task.errors.append(str(e))
        
        finally:
            # Finalize
            task.completed_at = datetime.now()
            task.execution_time_ms = (task.completed_at - start_time).total_seconds() * 1000
            
            # Update stats
            self.performance_stats['tasks_completed'] += 1
            self.performance_stats['total_processing_ms'] += task.execution_time_ms
            
            # Send response if from platform
            if task.platform_message:
                await self._send_platform_response(task)
            
            logger.info(f"Task {task.task_id} completed in {task.execution_time_ms:.2f}ms")
    
    async def _handle_consolidation(self, task: ProcessingTask):
        """Handle test consolidation task"""
        # This would integrate with existing ExcelProcessor
        logger.debug(f"Consolidating data from {len(task.input_data)} sources")
        
        # Learn format from input
        if task.input_data:
            first_record = task.input_data[0]
            task.learned_format = learning_engine.analyze_document(
                f"data_{task.task_id}", first_record.data
            )
        
        # Process consolidation
        task.results = {
            'records': len(task.input_data),
            'format': task.learned_format.format_id if task.learned_format else None
        }
    
    async def _handle_merge(self, task: ProcessingTask):
        """Handle table merge task"""
        logger.debug(f"Merging {len(task.input_data)} sources")
        
        # Intelligent table merging logic
        merged = {}
        for record in task.input_data:
            merged.update(record.data)
        
        task.results = {'merged_records': len(merged)}
    
    async def _handle_extraction(self, task: ProcessingTask):
        """Handle data extraction task"""
        logger.debug(f"Extracting from {len(task.input_data)} sources")
        
        extracted = []
        for record in task.input_data:
            if isinstance(record.data, dict):
                extracted.extend(record.data.values())
            elif isinstance(record.data, list):
                extracted.extend(record.data)
        
        task.results = {'extracted_items': len(extracted)}
    
    async def _handle_remote_fetch(self, task: ProcessingTask):
        """Handle remote data fetching"""
        logger.debug(f"Fetching from {len(task.input_sources)} remote sources")
        
        fetched_records = []
        for source in task.input_sources:
            if isinstance(source, str):
                # URL - need to convert to DataSource
                source = DataSource(
                    source_id=f"url_{len(task.input_sources)}",
                    source_type='api',
                    url=source
                )
            
            # Fetch from source
            records = await data_source_manager.fetch_from_source(source.source_id)
            fetched_records.extend(records)
        
        task.input_data = fetched_records
        task.results = {'fetched_records': len(fetched_records)}
    
    async def _handle_transform(self, task: ProcessingTask):
        """Handle data transformation"""
        logger.debug(f"Transforming {len(task.input_data)} records")
        
        # Get learned format for optimal strategy
        if task.input_data:
            strategy = learning_engine.get_processing_strategy(
                task.learned_format or DocumentFormat(
                    format_id="default",
                    file_extension="data",
                    source_app="universal"
                )
            )
            task.results = {'strategy': strategy, 'records_transformed': len(task.input_data)}
    
    async def _send_platform_response(self, task: ProcessingTask):
        """Send response back through platform"""
        if not task.platform_message:
            return
        
        response_text = self._format_response(task)
        response = PlatformResponse(text=response_text)
        
        # Send back to originating platform
        platform_name = task.platform_message.platform
        if platform_name in platform_bridge.adapters:
            adapter = platform_bridge.adapters[platform_name]
            await adapter.send_message(task.user_id, response)
    
    def _format_response(self, task: ProcessingTask) -> str:
        """Format task response"""
        status_emoji = {
            'completed': '[OK]',
            'failed': '❌',
            'processing': '⏳'
        }
        
        response = f"{status_emoji.get(task.status, '❓')} Task {task.task_type}\n"
        response += f"Status: {task.status}\n"
        response += f"Execution time: {task.execution_time_ms:.2f}ms\n"
        
        if task.results:
            response += f"Results: {task.results}\n"
        
        if task.errors:
            response += f"Errors: {'; '.join(task.errors)}\n"
        
        return response
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        stats = self.performance_stats.copy()
        if stats['tasks_completed'] > 0:
            stats['avg_processing_ms'] = stats['total_processing_ms'] / stats['tasks_completed']
        return stats
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'cache_size': len(self.cache),
            'cache_max': self.cache_size,
            'hits': self.performance_stats.get('cache_hits', 0),
            'misses': self.performance_stats.get('cache_misses', 0),
        }


# Global hypersonic core instance
hypersonic_core = HypersonicCore()
