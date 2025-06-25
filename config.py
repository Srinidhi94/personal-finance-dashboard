import os
from urllib.parse import quote_plus


class Config:
    """Base configuration"""

    SECRET_KEY = os.environ.get("SECRET_KEY") or "your-secret-key-change-in-production"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True

    # Feature Flags
    ENABLE_FILE_UPLOAD = os.environ.get("ENABLE_FILE_UPLOAD", "false").lower() in ("true", "1", "yes", "on")
    ENABLE_LLM_PARSING = os.environ.get("ENABLE_LLM_PARSING", "true").lower() in ("true", "1", "yes", "on")

    # Upload configuration
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER") or "uploads/"
    ALLOWED_EXTENSIONS = {"pdf", "csv", "xlsx", "xls", "txt"}
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_SIZE", 16 * 1024 * 1024))  # Default 16MB

    # File size limits (in bytes)
    MAX_PDF_SIZE = int(os.environ.get("MAX_PDF_SIZE", 32 * 1024 * 1024))  # 32MB for PDFs
    MAX_CSV_SIZE = int(os.environ.get("MAX_CSV_SIZE", 10 * 1024 * 1024))  # 10MB for CSV files
    MAX_EXCEL_SIZE = int(os.environ.get("MAX_EXCEL_SIZE", 25 * 1024 * 1024))  # 25MB for Excel files

    # LLM Configuration
    OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434"
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
    
    # LLM Settings
    LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", 60))  # Default 60 seconds
    LLM_MAX_RETRIES = int(os.environ.get("LLM_MAX_RETRIES", 3))  # Default 3 retries
    LLM_DEFAULT_MODEL = os.environ.get("LLM_DEFAULT_MODEL") or "gpt-4"

    # Redis configuration for session storage (optional)
    REDIS_URL = os.environ.get("REDIS_URL") or "redis://localhost:6379"

    # Security Configuration
    DB_ENCRYPTION_KEY = os.environ.get("DB_ENCRYPTION_KEY")

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True

    # Use SQLite for local development
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///personal_finance.db"

    # Enable file uploads in development by default
    ENABLE_FILE_UPLOAD = os.environ.get("ENABLE_FILE_UPLOAD", "true").lower() in ("true", "1", "yes", "on")


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False

    # PostgreSQL configuration for production (AWS RDS)
    DB_USER = os.environ.get("DB_USER") or "postgres"
    DB_PASSWORD = os.environ.get("DB_PASSWORD") or "password"
    DB_HOST = os.environ.get("DB_HOST") or "localhost"
    DB_PORT = os.environ.get("DB_PORT") or "5432"
    DB_NAME = os.environ.get("DB_NAME") or "personal_finance"

    # Construct PostgreSQL URL
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL") or f"postgresql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    # SSL mode for production
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

    # Production-specific settings
    ENABLE_FILE_UPLOAD = os.environ.get("ENABLE_FILE_UPLOAD", "false").lower() in ("true", "1", "yes", "on")

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # Log to stderr in production
        import logging
        from logging import StreamHandler

        file_handler = StreamHandler()
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)


class TestingConfig(Config):
    """Testing configuration"""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    
    # Testing-specific settings
    ENABLE_FILE_UPLOAD = True
    ENABLE_LLM_PARSING = False  # Disable LLM in tests by default
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1MB for testing


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
