from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: str = "development"
    app_secret_key: str = "change-me"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./linebook.db"

    # JWT
    jwt_secret_key: str = "change-me-jwt"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    # LINE
    line_channel_access_token: str = ""
    line_channel_secret: str = ""
    line_liff_id: str = ""

    # Google
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""
    google_scopes: str = "https://www.googleapis.com/auth/calendar"

    # CORS
    cors_origins: str = "http://localhost:3000"

    # URLs
    liff_base_url: str = ""
    admin_base_url: str = ""

    # AI
    anthropic_api_key: str = ""

    # Scheduler
    scheduler_enabled: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def google_scopes_list(self) -> list[str]:
        return [s.strip() for s in self.google_scopes.split(",") if s.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()
