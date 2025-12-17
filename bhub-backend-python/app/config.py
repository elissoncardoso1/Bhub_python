"""
Configurações da aplicação BHUB.
Utiliza pydantic-settings para validação e carregamento de variáveis de ambiente.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações principais da aplicação."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "BHUB"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"]
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("allowed_origins", mode="after")
    @classmethod
    def validate_origins_production(cls, v: list[str], info) -> list[str]:
        """Valida que não há wildcards em produção."""
        # Verificar se estamos validando para produção
        environment = info.data.get("environment", "development")
        
        if environment == "production":
            for origin in v:
                if "*" in origin or origin == "*":
                    raise ValueError(
                        "Wildcards não são permitidos em ALLOWED_ORIGINS em produção. "
                        "Especifique origens exatas."
                    )
                if not origin.startswith(("http://", "https://")):
                    raise ValueError(
                        f"Origem inválida: {origin}. Deve começar com http:// ou https://"
                    )
        return v

    # Database
    database_url: str = "sqlite+aiosqlite:///./bhub.db"

    # Security
    secret_key: str = Field(default="change-this-secret-key-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15  # 15 minutos (reduzido de 24h para segurança)
    refresh_token_expire_days: int = 7  # 7 dias para refresh tokens

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Valida que SECRET_KEY foi alterado em produção."""
        environment = info.data.get("environment", "development")
        
        if environment == "production":
            default_values = [
                "change-this-secret-key-in-production",
                "change-me-in-production",
                "secret",
                "changeme",
            ]
            if v in default_values or len(v) < 32:
                raise ValueError(
                    "SECRET_KEY deve ser alterado em produção e ter pelo menos 32 caracteres. "
                    "Gere uma chave segura com: openssl rand -hex 32"
                )
        return v

    # AI Services
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    huggingface_api_key: str | None = None

    # Image Services
    unsplash_access_key: str | None = None
    pexels_api_key: str | None = None

    # Cron
    cron_secret: str | None = None
    enable_scheduler: bool = True
    sync_interval_hours: int = 1

    # Paths
    base_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    upload_dir: Path = Field(default_factory=lambda: Path("./uploads"))
    log_dir: Path = Field(default_factory=lambda: Path("./logs"))

    @field_validator("upload_dir", "log_dir", mode="after")
    @classmethod
    def ensure_dir_exists(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        return v

    # PDF
    max_pdf_size_mb: int = 50
    pdf_upload_subdir: str = "pdfs"

    # ML
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    classification_threshold: float = 0.3

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # segundos

    # Logging
    log_level: str = "INFO"
    log_rotation: str = "10 MB"
    log_retention: str = "1 month"

    # Analytics
    enable_analytics: bool = True
    analytics_respect_dnt: bool = True  # Respeitar Do Not Track header

    @property
    def pdf_upload_path(self) -> Path:
        path = self.upload_dir / self.pdf_upload_subdir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @model_validator(mode="after")
    def validate_production_settings(self):
        """Validações adicionais para ambiente de produção."""
        if self.is_production:
            # Validar que DEBUG está desabilitado
            if self.debug:
                raise ValueError("DEBUG deve ser False em produção")
            
            # Validar que há pelo menos uma origem permitida
            if not self.allowed_origins:
                raise ValueError("ALLOWED_ORIGINS deve conter pelo menos uma origem em produção")
        
        return self


@lru_cache
def get_settings() -> Settings:
    """Retorna instância cacheada das configurações."""
    return Settings()


settings = get_settings()
