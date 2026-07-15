"""
Configuration for Mayz Monitoring Backend
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from parent directory (project root)
BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


def _get_required_env(key: str) -> str:
    """Get required environment variable or raise error."""
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Required environment variable {key} is not set. Copy .env.example to .env and fill in the values.")
    return value


def _get_secret_key() -> str:
    """Get SECRET_KEY from environment or raise error."""
    secret = os.getenv("SECRET_KEY")
    if not secret:
        raise ValueError(
            "SECRET_KEY is not set! "
            "Copy .env.example to .env and set a secure SECRET_KEY value. "
            "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )
    if secret == "CHANGE_THIS_TO_RANDOM_SECRET_KEY_MIN_32_CHARS":
        raise ValueError(
            "SECRET_KEY has not been changed from example value! "
            "Generate a secure key and update .env file."
        )
    return secret


# Security - Required values (will raise error if not set)
SECRET_KEY = _get_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8 hours

# MySQL Database (reuse existing config)
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "mayz_monitoring")

# App settings
APP_NAME = "Mayz Monitoring API"
APP_VERSION = "2.0.0"
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# CORS
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

# Export settings
EXPORT_DIR = BASE_DIR / "exports"
EXPORT_DIR.mkdir(exist_ok=True)
