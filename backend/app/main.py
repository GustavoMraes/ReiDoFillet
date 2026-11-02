from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.core.exceptions import registrar_handlers
from app.routers import auth, health, mesas


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.validar_seguranca()
    app = FastAPI(title="Rei do Filet - Atendimento e Comandas", version="0.1.0")
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_lista,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    registrar_handlers(app)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(mesas.router)
    return app


app = create_app()
