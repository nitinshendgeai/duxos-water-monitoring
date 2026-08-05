"""Application configuration, read from environment variables.

Railway injects DATABASE_URL automatically when a Postgres service is
attached in the same project. Everything else has a sane default so the
app also runs locally with minimal setup (see README).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/postgres"
    )

    # Default admin PIN seeded into app_config on first migration; changing
    # it afterwards is done via the Sheet-equivalent app_config table, not
    # this env var (matches prior Att_Config behavior).
    default_admin_pin: str = "1234"

    # Ariana Residency CHS is an Indian housing society; all "today" /
    # session-window calculations use this timezone, matching the Apps
    # Script backend's Session.getScriptTimeZone() behavior.
    timezone: str = "Asia/Kolkata"

    cors_origins: str = "*"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
