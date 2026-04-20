from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)

class ProcessingStrategy(Enum):

    STRICT = "strict"
    LENIENT = "lenient"
    ADAPTIVE = "adaptive"

class MergeStrategy(Enum):

    EMAIL = "email"
    NAME_EMAIL = "name_email"
    SEQUENCE = "sequence"
    FUZZY = "fuzzy"

class DataValidationLevel(Enum):

    MINIMAL = "minimal"
    STANDARD = "standard"
    STRICT = "strict"
    NONE = "none"

@dataclass
class ColumnMapping:

    name_variations: List[str] = field(default_factory=lambda: [
        'full name', 'full names', 'name', 'participant',
        'participant name', 'student name', 'person name'
    ])
    email_variations: List[str] = field(default_factory=lambda: [
        'email', 'email address', 'e-mail', 'contact email', 'user email'
    ])
    score_variations: List[str] = field(default_factory=lambda: [
        'score', 'result', 'test score', 'total score', 'percentage'
    ])

    def __post_init__(self):

        self.name_variations = [v.lower().strip() for v in self.name_variations]
        self.email_variations = [v.lower().strip() for v in self.email_variations]
        self.score_variations = [v.lower().strip() for v in self.score_variations]

@dataclass
class ColorConfig:

    colors: Dict[str, str] = field(default_factory=lambda: {
        'Test_1': 'FFFFFF',
        'Test_2': '87CEEB',
        'Test_3': 'FFFF00',
        'Test_4': '556B2F',
        'Test_5': 'FF0000',
        'Test_6': '800080',
        'Test_7': '00FFFF',
        'Test_8': 'FFA500',
        'Test_9': '90EE90',
        'Test_10': 'FFB6C1',
    })

    def get_color(self, test_name: str, default: str = 'FFFFFF') -> str:

        normalized = test_name.replace(' ', '_')
        return self.colors.get(normalized, default)

@dataclass
class BotConfig:

    input_folder: str = "input"
    output_folder: str = "output"
    file_pattern: str = "TEST_*.xlsx"
    case_sensitive_pattern: bool = False

    processing_strategy: ProcessingStrategy = ProcessingStrategy.ADAPTIVE
    merge_strategy: MergeStrategy = MergeStrategy.EMAIL
    min_files_required: int = 1
    max_files_allowed: int = 1000

    validation_level: DataValidationLevel = DataValidationLevel.STANDARD
    skip_invalid_rows: bool = True
    preserve_nan_values: bool = True

    column_mapping: ColumnMapping = field(default_factory=ColumnMapping)
    auto_detect_columns: bool = True
    case_insensitive_columns: bool = True

    sort_by: str = "name"
    remove_duplicates: bool = True
    remove_empty_rows: bool = True

    colors: ColorConfig = field(default_factory=ColorConfig)
    output_format: str = "xlsx"
    include_statistics: bool = True
    include_audit_trail: bool = True

    enable_agents: bool = True
    validation_agent_enabled: bool = True
    optimization_agent_enabled: bool = True
    quality_agent_enabled: bool = True
    auto_remediation_enabled: bool = True

    log_file: str = "compiler_execution.log"
    log_level: str = "INFO"
    verbose: bool = False

    @classmethod
    def from_json(cls, json_path: str) -> 'BotConfig':

        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            logger.info(f"Loaded configuration from {json_path}")
            return cls(**data)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {json_path}, using defaults")
            return cls()
        except Exception as e:
            logger.error(f"Error loading config: {e}, using defaults")
            return cls()

    def save_to_json(self, json_path: str) -> bool:

        try:
            config_dict = {
                'input_folder': self.input_folder,
                'output_folder': self.output_folder,
                'file_pattern': self.file_pattern,
                'case_sensitive_pattern': self.case_sensitive_pattern,
                'processing_strategy': self.processing_strategy.value,
                'merge_strategy': self.merge_strategy.value,
                'min_files_required': self.min_files_required,
                'max_files_allowed': self.max_files_allowed,
                'validation_level': self.validation_level.value,
                'skip_invalid_rows': self.skip_invalid_rows,
                'preserve_nan_values': self.preserve_nan_values,
                'auto_detect_columns': self.auto_detect_columns,
                'case_insensitive_columns': self.case_insensitive_columns,
                'sort_by': self.sort_by,
                'remove_duplicates': self.remove_duplicates,
                'remove_empty_rows': self.remove_empty_rows,
                'output_format': self.output_format,
                'include_statistics': self.include_statistics,
                'include_audit_trail': self.include_audit_trail,
                'enable_agents': self.enable_agents,
                'validation_agent_enabled': self.validation_agent_enabled,
                'optimization_agent_enabled': self.optimization_agent_enabled,
                'quality_agent_enabled': self.quality_agent_enabled,
                'auto_remediation_enabled': self.auto_remediation_enabled,
                'log_file': self.log_file,
                'log_level': self.log_level,
                'verbose': self.verbose,
            }
            with open(json_path, 'w') as f:
                json.dump(config_dict, f, indent=2)
            logger.info(f"Configuration saved to {json_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False

DEFAULT_CONFIG = BotConfig()

def get_default_config() -> BotConfig:

    return BotConfig()

def create_example_config(output_path: str = "config_example.json") -> bool:

    config = BotConfig()
    return config.save_to_json(output_path)

@dataclass
class ConversationalConfig:

    enable_intent_detection: bool = True
    enable_ocr: bool = False
    enable_pdf_parsing: bool = True
    max_conversation_history: int = 20
    intent_confidence_threshold: float = 0.7
    ocr_language: str = 'eng'
    pdf_extraction_mode: str = 'auto'
    enable_multi_format_support: bool = True
    enable_conversational_mode: bool = True

DEFAULT_CONVERSATIONAL_CONFIG = ConversationalConfig()

def get_default_conversational_config() -> ConversationalConfig:

    return ConversationalConfig()
