from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    anthropic_api_key: str
    notion_api_key: str
    notion_medical_reports_db_id: str
    notion_policies_db_id: str
    notion_decisions_db_id: str | None = None

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "info"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
