from app.core.config import Settings


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
