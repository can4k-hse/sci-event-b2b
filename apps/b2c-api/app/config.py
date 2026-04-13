from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://scievent:scievent@localhost:5432/scievent"

    jwt_secret_key: str = "dev-secret-key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15

    refresh_token_expire_days: int = 30

    otp_expire_minutes: int = 5
    otp_rate_limit_count: int = 5
    otp_rate_limit_window_minutes: int = 10

    app_env: str = "development"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:19006"]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
