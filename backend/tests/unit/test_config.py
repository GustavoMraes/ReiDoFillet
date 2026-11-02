import pytest

from app.core.config import Settings
from app.main import create_app


def test_carrega_configuracao_de_variaveis_de_ambiente(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:s@host/db")
    monkeypatch.setenv("CORS_ORIGINS", "https://reidofilet.vercel.app, http://localhost:5173")
    monkeypatch.setenv("TZ_EXIBICAO", "America/Sao_Paulo")

    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+asyncpg://u:s@host/db"
    assert settings.cors_origins_lista == ["https://reidofilet.vercel.app", "http://localhost:5173"]
    assert settings.tz_exibicao == "America/Sao_Paulo"


def test_cors_vazio_nao_libera_nenhuma_origem(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    assert Settings(_env_file=None).cors_origins_lista == []


@pytest.mark.parametrize("segredo", ["", "curta-demais"], ids=["ausente", "curta"])
def test_app_nao_sobe_sem_jwt_secret_adequada(segredo):
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        create_app(Settings(_env_file=None, jwt_secret=segredo))


def test_app_sobe_com_jwt_secret_valida():
    app = create_app(Settings(_env_file=None, jwt_secret="x" * 32))

    assert app.title


def test_expiracao_padrao_de_12_horas(monkeypatch):
    monkeypatch.delenv("JWT_EXPIRACAO_HORAS", raising=False)

    assert Settings(_env_file=None).jwt_expiracao_horas == 12
