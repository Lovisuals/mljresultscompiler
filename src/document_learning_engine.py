"""
Intelligent Document Format Learning Engine
Learns patterns from documents and adapts processing automatically
Uses ML to discover optimal processing strategies
"""

import json
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
import logging
from collections import Counter
import pickle
import os

logger = logging.getLogger(__name__)


@dataclass
class DocumentPattern:
    """Recognized pattern in document structure"""
    pattern_id: str
    pattern_type: str  # 'column_arrangement', 'data_type', 'naming_convention', etc.
    confidence: float
    pattern_data: Dict[str, Any]
    occurrences: int = 1
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)


@dataclass
class DocumentFormat:
    """Learned document format profile"""
    format_id: str
    file_extension: str
    source_app: str  # 'excel', 'csv', 'google_sheets', 'pdf', etc.
    column_patterns: Dict[str, str] = field(default_factory=dict)  # {column_idx: 'email', 'name', etc.}
    data_types: Dict[str, str] = field(default_factory=dict)  # {column_name: type}
    encoding: str = 'utf-8'
    patterns: List[DocumentPattern] = field(default_factory=list)
    confidence: float = 0.0
    sample_count: int = 0
    learning_data: Dict[str, Any] = field(default_factory=dict)


class DocumentLearningEngine:
    """ML engine that learns document formats"""
    
    def __init__(self, persistence_dir: str = 'models'):
        self.persistence_dir = persistence_dir
        self.learned_formats: Dict[str, DocumentFormat] = {}
        self.pattern_library: Dict[str, List[DocumentPattern]] = {}
        self.processing_history: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, float] = {}
        
        os.makedirs(persistence_dir, exist_ok=True)
        self._load_models()
    
    def analyze_document(self, file_path: str, content: Any) -> DocumentFormat:
        """Analyze document structure and learn format"""
        detected_format = DocumentFormat(
            format_id=f"fmt_{len(self.learned_formats)}",
            file_extension=file_path.split('.')[-1],
            source_app=self._detect_source_app(file_path, content)
        )
        
        # Extract patterns from content
        if isinstance(content, dict):
            detected_format = self._analyze_structured(content, detected_format)
        elif isinstance(content, list):
            detected_format = self._analyze_tabular(content, detected_format)
        elif isinstance(content, str):
            detected_format = self._analyze_text(content, detected_format)
        
        # Score confidence
        detected_format.confidence = self._calculate_confidence(detected_format)
        
        # Store learning
        self._store_format_learning(detected_format)
        
        return detected_format
    
    def _detect_source_app(self, file_path: str, content: Any) -> str:
        """Detect which application created the document"""
        ext = file_path.lower().split('.')[-1]
        
        if ext in ['xlsx', 'xls']:
            return 'excel'
        elif ext == 'csv':
            return 'csv'
        elif ext == 'pdf':
            return 'pdf'
        elif ext in ['json', 'jsonl']:
            return 'json'
        
        # Smart detection from content
        if isinstance(content, dict) and '_metadata' in content:
            return content.get('_source', 'unknown')
        
        return 'unknown'
    
    def _analyze_structured(self, data: Dict, fmt: DocumentFormat) -> DocumentFormat:
        """Analyze structured data (JSON, dicts)"""
        
        # Extract keys and types
        for key, value in data.items():
            data_type = type(value).__name__
            fmt.data_types[key] = data_type
            
            # Learn key naming patterns
            self._learn_key_pattern(key, fmt)
        
        fmt.sample_count += 1
        return fmt
    
    def _analyze_tabular(self, data: List, fmt: DocumentFormat) -> DocumentFormat:
        """Analyze tabular data (CSV, Excel, etc.)"""
        
        if not data:
            return fmt
        
        # Analyze first row as headers
        headers = data[0] if isinstance(data[0], list) else list(data[0].keys())
        
        for col_idx, header in enumerate(headers):
            header_str = str(header).lower().strip()
            
            # Detect column purpose
            purpose = self._detect_column_purpose(header_str)
            fmt.column_patterns[str(col_idx)] = purpose
            
            # Learn from samples
            if len(data) > 1:
                sample_values = [row[col_idx] if isinstance(row, list) else row.get(header)
                                for row in data[1:min(len(data), 10)]]
                data_type = self._infer_data_type(sample_values)
                fmt.data_types[header_str] = data_type
        
        fmt.sample_count += len(data)
        return fmt
    
    def _analyze_text(self, text: str, fmt: DocumentFormat) -> DocumentFormat:
        """Analyze unstructured text"""
        
        # Detect patterns
        lines = text.split('\n')
        
        # Check for common structures
        if self._looks_like_csv(text):
            fmt.source_app = 'csv_text'
            lines_data = [line.split(',') for line in lines[:10]]
            fmt = self._analyze_tabular(lines_data, fmt)
        elif self._looks_like_json(text):
            fmt.source_app = 'json_text'
            try:
                data = json.loads(text)
                fmt = self._analyze_structured(data, fmt)
            except:
                pass
        
        fmt.sample_count += 1
        return fmt
    
    def _learn_key_pattern(self, key: str, fmt: DocumentFormat):
        """Learn naming patterns in keys"""
        key_lower = key.lower()
        
        # Common patterns
        patterns = {
            'email': ['email', 'e-mail', 'mail', 'address'],
            'name': ['name', 'fullname', 'full_name', 'participant'],
            'score': ['score', 'result', 'percentage', '%', 'points'],
            'id': ['id', 'identifier', 'uid', 'code'],
            'date': ['date', 'timestamp', 'created', 'modified'],
            'phone': ['phone', 'tel', 'mobile', 'contact'],
        }
        
        for pattern_name, keywords in patterns.items():
            if any(kw in key_lower for kw in keywords):
                fmt.learning_data[f"key_pattern_{key}"] = pattern_name
    
    def _detect_column_purpose(self, header: str) -> str:
        """Detect what a column represents"""
        header_lower = header.lower()
        
        purposes = {
            'email': ['email', 'e-mail', 'mail'],
            'name': ['name', 'participant', 'fullname', 'full name'],
            'score': ['score', 'result', 'percentage', '%', 'points', 'mark'],
            'id': ['id', 'identifier', 'code', 'number'],
            'date': ['date', 'timestamp', 'created', 'modified', 'time'],
            'category': ['category', 'type', 'group', 'section'],
            'reference': ['ref', 'reference', 'link', 'url'],
        }
        
        for purpose, keywords in purposes.items():
            if any(kw in header_lower for kw in keywords):
                return purpose
        
        return 'unknown'
    
    def _infer_data_type(self, values: List) -> str:
        """Infer data type from sample values"""
        if not values:
            return 'unknown'
        
        types_found = Counter()
        
        for val in values:
            if val is None or val == '':
                continue
            
            val_str = str(val).strip()
            
            # Check type
            if val_str.replace('.', '').replace('-', '').isdigit():
                if '.' in val_str:
                    types_found['float'] += 1
                else:
                    types_found['int'] += 1
            elif '@' in val_str and '.' in val_str:
                types_found['email'] += 1
            elif len(val_str) < 100 and ' ' in val_str:
                types_found['text'] += 1
            else:
                types_found['string'] += 1
        
        if types_found:
            return types_found.most_common(1)[0][0]
        return 'string'
    
    def _looks_like_csv(self, text: str) -> bool:
        """Check if text looks like CSV"""
        lines = text.split('\n')[:5]
        comma_counts = [line.count(',') for line in lines]
        return len(set(comma_counts)) <= 1 and sum(comma_counts) > 0
    
    def _looks_like_json(self, text: str) -> bool:
        """Check if text looks like JSON"""
        text = text.strip()
        return (text.startswith('{') or text.startswith('[')) and \
               (text.endswith('}') or text.endswith(']'))
    
    def _calculate_confidence(self, fmt: DocumentFormat) -> float:
        """Calculate confidence score for detected format"""
        confidence = 0.0
        
        # More patterns = higher confidence
        pattern_count = len(fmt.column_patterns) + len(fmt.data_types)
        confidence += min(pattern_count * 0.1, 0.3)
        
        # More samples = higher confidence
        confidence += min(fmt.sample_count * 0.01, 0.4)
        
        # Matched known patterns = higher confidence
        if self._matches_known_pattern(fmt):
            confidence += 0.3
        
        return min(confidence, 1.0)
    
    def _matches_known_pattern(self, fmt: DocumentFormat) -> bool:
        """Check if format matches any known patterns"""
        for known_fmt in self.learned_formats.values():
            # Check similarity
            if len(fmt.column_patterns) == len(known_fmt.column_patterns):
                # Similar structure
                return True
        return False
    
    def _store_format_learning(self, fmt: DocumentFormat):
        """Store learned format for future use"""
        self.learned_formats[fmt.format_id] = fmt
        
        # Record processing history
        self.processing_history.append({
            'format_id': fmt.format_id,
            'confidence': fmt.confidence,
            'timestamp': datetime.now().isoformat()
        })
        
        # Save to disk
        self._save_models()
    
    def recommend_processor(self, file_path: str) -> Optional[str]:
        """Recommend processor based on learned patterns"""
        ext = file_path.split('.')[-1].lower()
        
        recommendations = {
            'xlsx': 'ExcelProcessor',
            'csv': 'CSVProcessor',
            'json': 'JSONProcessor',
            'pdf': 'PDFProcessor',
        }
        
        if ext in recommendations:
            return recommendations[ext]
        
        # Try to match against learned formats
        for fmt in self.learned_formats.values():
            if fmt.file_extension == ext and fmt.confidence > 0.7:
                if fmt.source_app == 'excel':
                    return 'ExcelProcessor'
                elif fmt.source_app == 'csv':
                    return 'CSVProcessor'
        
        return None
    
    def get_processing_strategy(self, fmt: DocumentFormat) -> Dict[str, Any]:
        """Generate optimal processing strategy for format"""
        return {
            'format_id': fmt.format_id,
            'column_mapping': fmt.column_patterns,
            'data_types': fmt.data_types,
            'encoding': fmt.encoding,
            'confidence': fmt.confidence,
            'optimizations': self._generate_optimizations(fmt)
        }
    
    def _generate_optimizations(self, fmt: DocumentFormat) -> List[str]:
        """Generate optimization hints"""
        optimizations = []
        
        if fmt.source_app == 'excel':
            optimizations.append('use_xlrd')  # Fast read
        elif fmt.source_app == 'csv':
            optimizations.append('use_chunking')  # Handle large files
        
        if fmt.confidence > 0.8:
            optimizations.append('skip_validation')  # Trust the format
        
        return optimizations
    
    def _save_models(self):
        """Persist models to disk"""
        try:
            models = {
                'formats': self.learned_formats,
                'patterns': self.pattern_library,
                'metrics': self.performance_metrics,
            }
            with open(f'{self.persistence_dir}/learned_models.pkl', 'wb') as f:
                pickle.dump(models, f)
            logger.debug("Models saved")
        except Exception as e:
            logger.error(f"Failed to save models: {e}")
    
    def _load_models(self):
        """Load persisted models from disk"""
        try:
            model_path = f'{self.persistence_dir}/learned_models.pkl'
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    models = pickle.load(f)
                self.learned_formats = models.get('formats', {})
                self.pattern_library = models.get('patterns', {})
                self.performance_metrics = models.get('metrics', {})
                logger.info(f"Loaded {len(self.learned_formats)} learned formats")
        except Exception as e:
            logger.error(f"Failed to load models: {e}")


# Global learning engine
learning_engine = DocumentLearningEngine()
