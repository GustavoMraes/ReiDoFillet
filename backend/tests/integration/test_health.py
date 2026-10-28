from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app

ORIGEM_PERMITIDA = "https://reidofilet.vercel.app"


def _cliente() -> AsyncClient:
    app = create_app(Settings(_env_file=None, cors_origins=ORIGEM_PERMITIDA))
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_health_responde_ok():
    async with _cliente() as cliente:
        resposta = await cliente.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


async def test_cors_libera_apenas_a_origem_configurada():
    async with _cliente() as cliente:
        permitida = await cliente.get("/health", headers={"Origin": ORIGEM_PERMITIDA})
        outra = await cliente.get("/health", headers={"Origin": "https://site-qualquer.com"})

    assert permitida.headers.get("access-control-allow-origin") == ORIGEM_PERMITIDA
    assert "access-control-allow-origin" not in outra.headers
