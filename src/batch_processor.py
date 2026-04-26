from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Optional
import json
from enum import Enum
import pandas as pd

class BatchStatus(Enum):

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ItemStatus(Enum):

    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class BatchItem:

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
            : self.item_id,
            : self.file_path,
            : self.test_numbers,
            : self.status.value,
            : self.result_file,
            : self.error,
            : self.started_at,
            : self.completed_at
        }

@dataclass
class BatchJob:

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
            : self.batch_id,
            : self.user_id,
            : self.status.value,
            : [item.to_dict() for item in self.items],
            : self.created_at,
            : self.started_at,
            : self.completed_at,
            : self.output_dir
        }

class BatchProcessor:

    def __init__(self, log_dir: str = "logs/batches"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.jobs: Dict[str, BatchJob] = {}

    def create_batch(self, batch_id: str, user_id: str, output_dir: str = None) -> BatchJob:

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

        if batch_id not in self.jobs:
            raise ValueError(f"Batch {batch_id} not found")

        batch = self.jobs[batch_id]
        batch.status = BatchStatus.PROCESSING
        batch.started_at = datetime.now().isoformat()
        self._log_batch(batch)
        return batch

    def mark_item_processing(self, batch_id: str, item_id: str) -> BatchItem:

        batch = self._get_batch(batch_id)
        item = self._get_item(batch, item_id)
        item.status = ItemStatus.PROCESSING
        item.started_at = datetime.now().isoformat()
        self._log_batch(batch)
        return item

    def mark_item_success(self, batch_id: str, item_id: str, result_file: str) -> BatchItem:

        batch = self._get_batch(batch_id)
        item = self._get_item(batch, item_id)
        item.status = ItemStatus.SUCCESS
        item.result_file = result_file
        item.completed_at = datetime.now().isoformat()
        self._log_batch(batch)
        return item

    def mark_item_failed(self, batch_id: str, item_id: str, error: str) -> BatchItem:

        batch = self._get_batch(batch_id)
        item = self._get_item(batch, item_id)
        item.status = ItemStatus.FAILED
        item.error = error
        item.completed_at = datetime.now().isoformat()
        self._log_batch(batch)
        return item

    def complete_batch(self, batch_id: str) -> BatchJob:

        batch = self._get_batch(batch_id)
        batch.status = BatchStatus.COMPLETED
        batch.completed_at = datetime.now().isoformat()
        self._log_batch(batch)
        return batch

    def get_batch_progress(self, batch_id: str) -> Dict:

        batch = self._get_batch(batch_id)

        total = len(batch.items)
        completed = sum(1 for item in batch.items if item.status in [ItemStatus.SUCCESS, ItemStatus.FAILED])
        success = sum(1 for item in batch.items if item.status == ItemStatus.SUCCESS)
        failed = sum(1 for item in batch.items if item.status == ItemStatus.FAILED)

        return {
            : batch_id,
            : batch.status.value,
            : total,
            : completed,
            : success,
            : failed,
            : int((completed / total * 100) if total > 0 else 0),
            : batch.created_at,
            : batch.started_at,
            : batch.completed_at,
            : batch.output_dir
        }

    def get_batch_report(self, batch_id: str) -> Dict:

        batch = self._get_batch(batch_id)
        progress = self.get_batch_progress(batch_id)

        report = {
            : progress,
            : [item.to_dict() for item in batch.items],
            : {
                : len(batch.items),
                : sum(1 for item in batch.items if item.status == ItemStatus.SUCCESS),
                : sum(1 for item in batch.items if item.status == ItemStatus.FAILED),
                : sum(1 for item in batch.items if item.status == ItemStatus.PENDING),
                : f"{progress['progress_percent']}%"
            }
        }

        return report

    def export_batch_report(self, batch_id: str, output_file: str = None) -> str:

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

        if batch_id not in self.jobs:
            raise ValueError(f"Batch {batch_id} not found")
        return self.jobs[batch_id]

    def _get_item(self, batch: BatchJob, item_id: str) -> BatchItem:

        for item in batch.items:
            if item.item_id == item_id:
                return item
        raise ValueError(f"Item {item_id} not found in batch")

    def _log_batch(self, batch: BatchJob):

        log_file = self.log_dir / f"batch_{batch.batch_id}.jsonl"

        with open(log_file, 'a') as f:
            log_entry = {
                : datetime.now().isoformat(),
                : batch.to_dict()
            }
            f.write(json.dumps(log_entry) + '\n')

    def consolidate_multiple_files(self, file_list: List[Dict], output_dir: str) -> Dict:

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

                processor = ExcelProcessor()
                dataframes = processor.load_test_file(str(file_path))

                if not dataframes:
                    raise ValueError(f"No test data found in {file_path}")

                consolidated = processor.consolidate_results(dataframes)

                result_file = output_path / f"consolidated_{idx}.xlsx"
                test_nums = list(dataframes.keys()) if not test_numbers else test_numbers
                processor.save_consolidated_file(consolidated, test_nums, result_file)

                self.mark_item_success(batch_id, item_id, str(result_file))
                results.append({
                    : file_info['path'],
                    : 'success',
                    : str(result_file),
                    : len(consolidated)
                })

            except Exception as e:
                self.mark_item_failed(batch_id, item_id, str(e))
                results.append({
                    : file_info['path'],
                    : 'failed',
                    : str(e)
                })

        self.complete_batch(batch_id)

        report_file = self.export_batch_report(batch_id)

        return {
            : batch_id,
            : output_dir,
            : results,
            : report_file,
            : self.get_batch_progress(batch_id)
        }
