"""Application configuration via pydantic-settings.

Environment variables are validated when :func:`get_settings` is first called
(fail fast). Required: ``SECRET_KEY``, ``ALLOWED_ORIGINS``, ``ADMIN_USERNAME``,
``ADMIN_PASSWORD``.
"""

from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings read from environment variables (or a ``.env`` file)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Data layer -------------------------------------------------------
    database_url: str = "sqlite+aiosqlite:///./bibliotheca.db"

    # --- Security ---------------------------------------------------------
    # HS256 JWT signing key (accepts SECRET_KEY or JWT_SECRET).
    secret_key: str = Field(
        validation_alias=AliasChoices("SECRET_KEY", "JWT_SECRET")
    )
    # Comma-separated CORS allowlist. Never "*" when credentials are enabled.
    allowed_origins: str

    # --- Admin bootstrap --------------------------------------------------
    admin_username: str
    admin_password: str

    # --- Business data (PDF invoice header) -------------------------------
    business_name: str = ""
    business_cuit: str = ""
    business_address: str = ""
    business_condition: str = ""

    # --- Catalog ----------------------------------------------------------
    low_stock_threshold: int = 5

    # --- Rate limiting ----------------------------------------------------
    rate_limit_login: str = "5/minute"
    rate_limit_api: str = "60/minute"

    # --- Auth -------------------------------------------------------------
    access_token_expire_minutes: int = 60

    @field_validator("secret_key", "admin_username", "admin_password")
    @classmethod
    def _require_non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must be a non-empty string")
        return value

    @field_validator("allowed_origins")
    @classmethod
    def _validate_origins(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("ALLOWED_ORIGINS must not be empty")
        origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        if "*" in origins:
            raise ValueError(
                "ALLOWED_ORIGINS must not contain '*' (wildcard is incompatible "
                "with allow_credentials=True)"
            )
        return value

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse the comma-separated allowlist into a clean list."""
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (fail fast on missing required vars)."""
    return Settings()
