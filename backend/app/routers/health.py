from fastapi import APIRouter

router = APIRouter(tags=["Infraestrutura"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Usado pelo UptimeRobot para manter o serviço do Render ativo. Não acessa o banco."""
    return {"status": "ok"}
