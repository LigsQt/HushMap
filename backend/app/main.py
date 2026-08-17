from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.security import DeviceAuthenticator, SlidingWindowRateLimiter
from app.database import create_engine, create_session_factory
from app.routers import audio, health, points
from app.services.ai import create_ai_provider
from app.services.audio_ingest import AudioBufferStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    ai_provider = create_ai_provider(settings)
    audio_store = AudioBufferStore(
        target_bytes=settings.audio_window_bytes,
        max_chunk_bytes=settings.audio_max_chunk_bytes,
        max_buffer_bytes=settings.audio_max_buffer_bytes,
        ttl_seconds=settings.audio_buffer_ttl_seconds,
        max_active_sessions=settings.audio_max_active_sessions,
        max_active_sessions_per_owner=settings.audio_max_active_sessions_per_device,
        max_recent_idempotency_keys=settings.audio_max_recent_idempotency_keys,
    )

    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.ai_provider = ai_provider
    app.state.audio_store = audio_store
    app.state.device_auth = DeviceAuthenticator(settings.device_api_keys)
    app.state.upload_limiter = SlidingWindowRateLimiter(settings.upload_rate_limit_per_minute)
    app.state.summary_request_limiter = SlidingWindowRateLimiter(
        settings.summary_request_rate_limit_per_minute
    )
    app.state.summary_global_limiter = SlidingWindowRateLimiter(
        settings.summary_global_rate_limit_per_minute
    )

    try:
        yield
    finally:
        await ai_provider.close()
        if engine is not None:
            await engine.dispose()


app = FastAPI(title="HushMap API", lifespan=lifespan)
app.include_router(health.router)
app.include_router(points.router)
app.include_router(audio.router)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Working!"}
