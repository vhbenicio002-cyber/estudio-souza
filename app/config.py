import os
from pathlib import Path
from functools import lru_cache

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_file():
    """Load project .env before reading settings; existing environment wins."""
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=False)
    except ImportError:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file()


class Settings:
    def __init__(self):
        self.APP_NAME = os.getenv("APP_NAME", "Estúdio Souza")
        self.APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        self.ENABLE_BACKGROUND_JOBS = os.getenv("ENABLE_BACKGROUND_JOBS", "false").lower() == "true"
        self.SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key-before-production")
        self.ALGORITHM = os.getenv("ALGORITHM", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))

        database_url = os.getenv("DATABASE_URL", "sqlite:///./barbearia.db")
        if database_url.startswith("sqlite:///./"):
            database_url = "sqlite:///" + str((BASE_DIR / database_url[len("sqlite:///./"):]).resolve())
        elif database_url.startswith("postgres://"):
            database_url = "postgresql+psycopg://" + database_url[len("postgres://"):]
        elif database_url.startswith("postgresql://"):
            database_url = "postgresql+psycopg://" + database_url[len("postgresql://"):]
        self.DATABASE_URL = database_url

        self.WHATSAPP_PROVIDER = os.getenv("WHATSAPP_PROVIDER", "mock")
        self.WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL", "")
        self.WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN", "")
        self.WHATSAPP_INSTANCE_ID = os.getenv("WHATSAPP_INSTANCE_ID", "")
        self.WHATSAPP_FROM_NUMBER = os.getenv("WHATSAPP_FROM_NUMBER", "")

        self.FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8000")
        self.ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@barbearia.com")
        self.ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
        self.TIMEZONE = os.getenv("TIMEZONE", "America/Fortaleza")


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
