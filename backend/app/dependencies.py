from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.services.ai import AIProvider
from app.services.audio_ingest import AudioBufferStore


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_ai_provider(request: Request) -> AIProvider:
    return request.app.state.ai_provider


def get_audio_store(request: Request) -> AudioBufferStore:
    return request.app.state.audio_store


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    factory = request.app.state.session_factory
    if factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured",
        )
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
AIProviderDep = Annotated[AIProvider, Depends(get_ai_provider)]
AudioStoreDep = Annotated[AudioBufferStore, Depends(get_audio_store)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
