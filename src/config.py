import os
from pathlib import Path
from typing import Optional
try:

    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic import Field, field_validator
    ConfigDict = SettingsConfigDict
except (ImportError, ModuleNotFoundError):
    try:

        from pydantic import BaseSettings, Field, validator
        field_validator = validator
        ConfigDict = None
    except Exception:

        from pydantic import Field
        try:
            from pydantic.v1 import BaseSettings, validator
            field_validator = validator
            ConfigDict = None
        except ImportError:
            raise ImportError("Could not import BaseSettings. Please install 'pydantic-settings' for Pydantic V2.")

class Settings(BaseSettings):

    APP_NAME: str = "MLJ Results Compiler"
    APP_VERSION: str = "0.2.0"
    DEBUG: bool = False
    ENV: str = "development"

    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "sqlite:///data/sessions.db"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    TELEGRAM_BOT_TOKEN: Optional[str] = None
    MLJCM_BOT_TOKEN: Optional[str] = None
    WEBHOOK_BASE_URL: Optional[str] = None

    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.1-70b-versatile"
    GROQ_TIMEOUT: int = 30

    ENABLE_AI_ASSISTANT: bool = False
    ENABLE_TELEGRAM_BOT: bool = False

    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024
    UPLOAD_DIR: Path = Path("temp_uploads")
    OUTPUT_DIR: Path = Path("output")

    SESSION_TIMEOUT: int = 3600
    CLEANUP_INTERVAL: int = 3600

    WORKERS: int = 4
    RELOAD: bool = False

    if ConfigDict is not None:
        model_config = ConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=True,
            extra="allow"
        )
    else:
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            case_sensitive = True
            extra = "allow"

    if ConfigDict is not None:
        @field_validator("ENABLE_AI_ASSISTANT", mode="before")
        @classmethod
        def set_ai_enabled(cls, v, info):

            values = info.data if hasattr(info, 'data') else {}
            return bool(values.get("GROQ_API_KEY"))

        @field_validator("ENABLE_TELEGRAM_BOT", mode="before")
        @classmethod
        def set_telegram_enabled(cls, v, info):

            values = info.data if hasattr(info, 'data') else {}
            return bool(values.get("TELEGRAM_BOT_TOKEN"))

        @field_validator("ENV")
        @classmethod
        def validate_env(cls, v):

            valid = ["development", "staging", "production"]
            if v not in valid:
                raise ValueError(f"ENV must be one of {valid}")
            return v
    else:
        @validator("ENABLE_AI_ASSISTANT", pre=True, allow_reuse=True)
        def set_ai_enabled(cls, v, values):

            return bool(values.get("GROQ_API_KEY"))

        @validator("ENABLE_TELEGRAM_BOT", pre=True, allow_reuse=True)
        def set_telegram_enabled(cls, v, values):

            return bool(values.get("TELEGRAM_BOT_TOKEN"))

        @validator("ENV", allow_reuse=True)
        def validate_env(cls, v):

            valid = ["development", "staging", "production"]
            if v not in valid:
                raise ValueError(f"ENV must be one of {valid}")
            return v

    def __init__(self, **data):

        super().__init__(**data)

        if self.ENV == "production":
            if not self.TELEGRAM_BOT_TOKEN:
                raise ValueError("TELEGRAM_BOT_TOKEN required for production")
            if not self.WEBHOOK_BASE_URL:
                raise ValueError("WEBHOOK_BASE_URL required for production")
            if not self.DATABASE_URL.startswith("postgresql://"):
                raise ValueError("PostgreSQL required for production (not SQLite)")

        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

settings: Optional[Settings] = None

def get_settings() -> Settings:

    global settings
    if settings is None:
        settings = Settings()
    return settings

def validate_settings():

    s = get_settings()

    errors = []
    warnings = []

    if s.ENABLE_TELEGRAM_BOT and not s.TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN not set but bot enabled")

    if s.ENABLE_TELEGRAM_BOT and not s.WEBHOOK_BASE_URL:
        warnings.append("WEBHOOK_BASE_URL not set - bot will use polling mode (this is fine)")

    if s.ENABLE_AI_ASSISTANT and not s.GROQ_API_KEY:
        errors.append("GROQ_API_KEY not set but AI enabled")

    if warnings:
        import logging
        logger = logging.getLogger(__name__)
        for w in warnings:
            logger.warning(f"  ⚠ {w}")

    if errors:
        error_msg = "Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
        raise RuntimeError(error_msg)

    return True
