import os
from urllib.parse import quote_plus


class Config:
    """Base configuration"""

    SECRET_KEY = os.environ.get("SECRET_KEY") or "your-secret-key-change-in-production"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True

    # Upload configuration
    UPLOAD_FOLDER = "uploads/"
    ALLOWED_EXTENSIONS = {"pdf", "csv", "txt"}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max

    # Redis configuration for session storage (optional)
    REDIS_URL = os.environ.get("REDIS_URL") or "redis://localhost:6379"

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True

    # Use SQLite for local development
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///personal_finance.db"


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


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
