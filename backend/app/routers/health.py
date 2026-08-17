from fastapi import APIRouter, Request

from app.database import database_is_ready

router = APIRouter()


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(request: Request) -> dict[str, object]:
    db_ready = await database_is_ready(request.app.state.engine)
    ai_ready = request.app.state.ai_provider.ready
    status = "ok" if db_ready else "degraded"
    return {
        "status": status,
        "database": db_ready,
        "ai": ai_ready,
        "ai_mode": request.app.state.settings.ai_mode.value,
    }
