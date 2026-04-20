"""
Batch Processing Module for Multiple Consolidations
Handles queuing, progress tracking, and batch reporting
"""

from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Optional
import json
from enum import Enum
import pandas as pd


class BatchStatus(Enum):
    """Batch processing status"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ItemStatus(Enum):
    """Individual item status"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class BatchItem:
    """Single batch item"""
    item_id: str
    file_path: str
    test_numbers: List[int]
    status: ItemStatus = ItemStatus.PENDING
    result_file: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    def to_dict(self):
        return {
            'item_id': self.item_id,
            'file_path': self.file_path,
            'test_numbers': self.test_numbers,
            'status': self.status.value,
            'result_file': self.result_file,
            'error': self.error,
            'started_at': self.started_at,
            'completed_at': self.completed_at
        }


@dataclass
class BatchJob:
    """Batch processing job"""
    batch_id: str
    user_id: str
    status: BatchStatus = BatchStatus.QUEUED
    items: List[BatchItem] = None
    created_at: str = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    output_dir: Optional[str] = None
    
    def __post_init__(self):
        if self.items is None:
            self.items = []
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self):
        return {
            'batch_id': self.batch_id,
            'user_id': self.user_id,
            'status': self.status.value,
            'items': [item.to_dict() for item in self.items],
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'output_dir': self.output_dir
        }


class BatchProcessor:
    """Process multiple consolidations in batch"""
    
    def __init__(self, log_dir: str = "logs/batches"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.jobs: Dict[str, BatchJob] = {}
    
    def create_batch(self, batch_id: str, user_id: str, output_dir: str = None) -> BatchJob:
        """Create new batch job"""
        batch = BatchJob(
            batch_id=batch_id,
            user_id=user_id,
            output_dir=output_dir or f"output/batch_{batch_id}"
        )
        self.jobs[batch_id] = batch
        self._log_batch(batch)
        return batch
    
    def add_item_to_batch(self, batch_id: str, item_id: str, file_path: str, 
                         test_numbers: List[int]) -> BatchItem:
        """Add item to batch"""
        if batch_id not in self.jobs:
            raise ValueError(f"Batch {batch_id} not found")
        
        item = BatchItem(
            item_id=item_id,
            file_path=file_path,
            test_numbers=test_numbers
        )
        self.jobs[batch_id].items.append(item)
        return item
    
    def start_batch(self, batch_id: str) -> BatchJob:
        """Start batch processing"""
        if batch_id not in self.jobs:
            raise ValueError(f"Batch {batch_id} not found")
        
        batch = self.jobs[batch_id]
        batch.status = BatchStatus.PROCESSING
        batch.started_at = datetime.now().isoformat()
        self._log_batch(batch)
        return batch
    
    def mark_item_processing(self, batch_id: str, item_id: str) -> BatchItem:
        """Mark item as processing"""
        batch = self._get_batch(batch_id)
        item = self._get_item(batch, item_id)
        item.status = ItemStatus.PROCESSING
        item.started_at = datetime.now().isoformat()
        self._log_batch(batch)
        return item
    
    def mark_item_success(self, batch_id: str, item_id: str, result_file: str) -> BatchItem:
        """Mark item as successfully completed"""
        batch = self._get_batch(batch_id)
        item = self._get_item(batch, item_id)
        item.status = ItemStatus.SUCCESS
        item.result_file = result_file
        item.completed_at = datetime.now().isoformat()
        self._log_batch(batch)
        return item
    
    def mark_item_failed(self, batch_id: str, item_id: str, error: str) -> BatchItem:
        """Mark item as failed"""
        batch = self._get_batch(batch_id)
        item = self._get_item(batch, item_id)
        item.status = ItemStatus.FAILED
        item.error = error
        item.completed_at = datetime.now().isoformat()
        self._log_batch(batch)
        return item
    
    def complete_batch(self, batch_id: str) -> BatchJob:
        """Complete batch job"""
        batch = self._get_batch(batch_id)
        batch.status = BatchStatus.COMPLETED
        batch.completed_at = datetime.now().isoformat()
        self._log_batch(batch)
        return batch
    
    def get_batch_progress(self, batch_id: str) -> Dict:
        """Get batch progress summary"""
        batch = self._get_batch(batch_id)
        
        total = len(batch.items)
        completed = sum(1 for item in batch.items if item.status in [ItemStatus.SUCCESS, ItemStatus.FAILED])
        success = sum(1 for item in batch.items if item.status == ItemStatus.SUCCESS)
        failed = sum(1 for item in batch.items if item.status == ItemStatus.FAILED)
        
        return {
            'batch_id': batch_id,
            'status': batch.status.value,
            'total_items': total,
            'completed': completed,
            'successful': success,
            'failed': failed,
            'progress_percent': int((completed / total * 100) if total > 0 else 0),
            'created_at': batch.created_at,
            'started_at': batch.started_at,
            'completed_at': batch.completed_at,
            'output_dir': batch.output_dir
        }
    
    def get_batch_report(self, batch_id: str) -> Dict:
        """Generate detailed batch report"""
        batch = self._get_batch(batch_id)
        progress = self.get_batch_progress(batch_id)
        
        report = {
            'summary': progress,
            'items': [item.to_dict() for item in batch.items],
            'statistics': {
                'total_items': len(batch.items),
                'successful_items': sum(1 for item in batch.items if item.status == ItemStatus.SUCCESS),
                'failed_items': sum(1 for item in batch.items if item.status == ItemStatus.FAILED),
                'pending_items': sum(1 for item in batch.items if item.status == ItemStatus.PENDING),
                'success_rate': f"{progress['progress_percent']}%"
            }
        }
        
        return report
    
    def export_batch_report(self, batch_id: str, output_file: str = None) -> str:
        """Export batch report to JSON"""
        batch = self._get_batch(batch_id)
        report = self.get_batch_report(batch_id)
        
        if output_file is None:
            output_file = self.log_dir / f"batch_{batch_id}_report.json"
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        return str(output_path)
    
    def _get_batch(self, batch_id: str) -> BatchJob:
        """Get batch by ID"""
        if batch_id not in self.jobs:
            raise ValueError(f"Batch {batch_id} not found")
        return self.jobs[batch_id]
    
    def _get_item(self, batch: BatchJob, item_id: str) -> BatchItem:
        """Get item from batch"""
        for item in batch.items:
            if item.item_id == item_id:
                return item
        raise ValueError(f"Item {item_id} not found in batch")
    
    def _log_batch(self, batch: BatchJob):
        """Log batch state to JSONL"""
        log_file = self.log_dir / f"batch_{batch.batch_id}.jsonl"
        
        with open(log_file, 'a') as f:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'batch': batch.to_dict()
            }
            f.write(json.dumps(log_entry) + '\n')
    
    def consolidate_multiple_files(self, file_list: List[Dict], output_dir: str) -> Dict:
        """
        Consolidate multiple test files in batch
        
        Args:
            file_list: List of dicts with 'path' and 'test_numbers'
            output_dir: Output directory for results
        
        Returns:
            Dictionary with results and summary
        """
        from src.excel_processor import ExcelProcessor
        
        batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch = self.create_batch(batch_id, "batch_user", output_dir)
        self.start_batch(batch_id)
        
        results = []
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for idx, file_info in enumerate(file_list):
            item_id = f"file_{idx}"
            
            try:
                self.mark_item_processing(batch_id, item_id)
                
                file_path = Path(file_info['path'])
                test_numbers = file_info.get('test_numbers', [])
                
                if not file_path.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")
                
                # Process file
                processor = ExcelProcessor()
                dataframes = processor.load_test_file(str(file_path))
                
                if not dataframes:
                    raise ValueError(f"No test data found in {file_path}")
                
                # Consolidate
                consolidated = processor.consolidate_results(dataframes)
                
                # Save result
                result_file = output_path / f"consolidated_{idx}.xlsx"
                test_nums = list(dataframes.keys()) if not test_numbers else test_numbers
                processor.save_consolidated_file(consolidated, test_nums, result_file)
                
                self.mark_item_success(batch_id, item_id, str(result_file))
                results.append({
                    'file': file_info['path'],
                    'status': 'success',
                    'output': str(result_file),
                    'participants': len(consolidated)
                })
                
            except Exception as e:
                self.mark_item_failed(batch_id, item_id, str(e))
                results.append({
                    'file': file_info['path'],
                    'status': 'failed',
                    'error': str(e)
                })
        
        self.complete_batch(batch_id)
        
        # Generate report
        report_file = self.export_batch_report(batch_id)
        
        return {
            'batch_id': batch_id,
            'output_dir': output_dir,
            'results': results,
            'report_file': report_file,
            'progress': self.get_batch_progress(batch_id)
        }
