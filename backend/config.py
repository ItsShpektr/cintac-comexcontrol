from functools import lru_cache
from pathlib import Path
import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict


# Se crea una sola vez por proceso para que los JWT sigan siendo válidos durante
# toda la ejecución local aun cuando el desarrollador todavía no tenga .env.
_DEV_SECRET = secrets.token_urlsafe(48)


class Settings(BaseSettings):
    app_name: str = "CINTAC ComexControl API"
    environment: str = "development"
    database_url: str = "sqlite:///./comexcontrol.db"
    secret_key: str | None = None
    access_token_expire_minutes: int = 60
    cors_origins: str = "http://localhost:5173"
    bootstrap_admin_name: str | None = None
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    max_upload_mb: int = 5

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def normalized_database_url(self) -> str:
        url = self.database_url.strip()
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def jwt_secret(self) -> str:
        if self.secret_key:
            if self.environment.lower() == "production" and len(self.secret_key) < 32:
                raise RuntimeError("SECRET_KEY debe tener al menos 32 caracteres en producción")
            return self.secret_key
        if self.environment.lower() == "production":
            raise RuntimeError("SECRET_KEY es obligatoria en producción")
        return _DEV_SECRET


@lru_cache
def get_settings() -> Settings:
    return Settings()
