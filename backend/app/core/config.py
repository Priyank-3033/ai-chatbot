from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")
    auth_secret: str = Field(default="change-me-dev-secret", alias="AUTH_SECRET")
    auth_token_ttl_hours: int = Field(default=72, alias="AUTH_TOKEN_TTL_HOURS")
    database_path_raw: str = Field(default="./app_data.sqlite3", alias="DATABASE_PATH")
    admin_emails_raw: str = Field(default="admin@smartcommerce.ai", alias="ADMIN_EMAILS")
    api_title: str = Field(default="Smart AI Commerce API", alias="API_TITLE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,
    )

    @property
    def backend_dir(self) -> Path:
        return BACKEND_DIR

    @property
    def knowledge_base_path(self) -> Path:
        return self.backend_dir / "app" / "data" / "support_docs.md"

    @property
    def product_catalog_path(self) -> Path:
        return self.backend_dir / "app" / "data" / "products.json"

    @property
    def database_path(self) -> Path:
        raw = Path(self.database_path_raw)
        return raw if raw.is_absolute() else self.backend_dir / raw

    @property
    def frontend_public_path(self) -> Path:
        return BACKEND_DIR.parent / "frontend" / "public"

    @property
    def product_photos_path(self) -> Path:
        return self.frontend_public_path / "product-photos"

    @property
    def parsed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def admin_emails(self) -> set[str]:
        return {email.strip().lower() for email in self.admin_emails_raw.split(",") if email.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
