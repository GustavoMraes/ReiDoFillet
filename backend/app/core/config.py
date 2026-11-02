from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

TAMANHO_MINIMO_JWT_SECRET = 32


class Settings(BaseSettings):
    """Configuração central, lida de variáveis de ambiente (ou do arquivo .env)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = ""
    cors_origins: str = ""
    tz_exibicao: str = "America/Sao_Paulo"
    test_database_url: str | None = None
    jwt_secret: str = ""
    jwt_expiracao_horas: float = 12

    def validar_seguranca(self) -> None:
        """Impede a aplicação de subir sem uma chave de assinatura de token adequada."""
        if len(self.jwt_secret) < TAMANHO_MINIMO_JWT_SECRET:
            raise RuntimeError(
                f"JWT_SECRET ausente ou curta: são necessários pelo menos {TAMANHO_MINIMO_JWT_SECRET} caracteres"
            )
        if self.jwt_expiracao_horas <= 0:
            raise RuntimeError("JWT_EXPIRACAO_HORAS deve ser maior que zero")

    @property
    def cors_origins_lista(self) -> list[str]:
        return [origem.strip() for origem in self.cors_origins.split(",") if origem.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
