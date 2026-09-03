from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIRECTORY = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "VeriGate API"
    app_version: str = "0.1.0"
    database_url: str
    auth_secret_key: str
    access_token_expire_minutes: int = 30
    password_reset_expire_minutes: int = 20
    gmail_username: str = ""
    gmail_app_password: str = ""
    email_from_name: str = "VeriGate"
    frontend_url: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIRECTORY / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
