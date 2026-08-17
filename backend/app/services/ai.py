import asyncio
import os
import random
import tempfile
from pathlib import Path
from typing import Protocol

import httpx

from app.config import AIMode, Settings
from app.services.prompts import AUDIO_DESCRIPTION_PROMPT_V1, session_summary_prompt


class AIProviderError(RuntimeError):
    pass


class AIProvider(Protocol):
    @property
    def ready(self) -> bool: ...

    async def describe_audio(self, audio: bytes) -> str: ...

    async def summarize_descriptions(self, descriptions: str) -> str: ...

    async def close(self) -> None: ...


class UnavailableAIProvider:
    def __init__(self, reason: str) -> None:
        self._reason = reason

    @property
    def ready(self) -> bool:
        return False

    async def describe_audio(self, audio: bytes) -> str:
        raise AIProviderError(self._reason)

    async def summarize_descriptions(self, descriptions: str) -> str:
        raise AIProviderError(self._reason)

    async def close(self) -> None:
        return None


class RemoteAIProvider:
    def __init__(self, endpoint: str, timeout: float) -> None:
        self._endpoint = endpoint.rstrip("/") + "/"
        self._client = httpx.AsyncClient(timeout=timeout)

    @property
    def ready(self) -> bool:
        return True

    async def describe_audio(self, audio: bytes) -> str:
        try:
            response = await self._client.post(
                f"{self._endpoint}describe",
                files={"file": ("recording.wav", audio, "audio/wav")},
            )
            response.raise_for_status()
            return str(response.json().get("description", "No description found"))
        except (httpx.HTTPError, ValueError) as exc:
            raise AIProviderError("Remote AI description failed") from exc

    async def summarize_descriptions(self, descriptions: str) -> str:
        try:
            response = await self._client.post(
                f"{self._endpoint}summarize",
                params={"descriptions": descriptions},
            )
            response.raise_for_status()
            return str(
                response.json().get(
                    "summary",
                    "Error generating AI response, please try again!",
                )
            )
        except (httpx.HTTPError, ValueError) as exc:
            raise AIProviderError("Remote AI summarization failed") from exc

    async def close(self) -> None:
        await self._client.aclose()


class GeminiAIProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout: float,
        max_retries: int,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries
        self._client = None

    @property
    def ready(self) -> bool:
        return bool(self._api_key)

    def _get_client(self):
        if self._client is None:
            from google import genai
            from google.genai import types

            self._client = genai.Client(
                api_key=self._api_key,
                http_options=types.HttpOptions(timeout=int(self._timeout * 1000)),
            )
        return self._client

    async def _retry(self, operation):
        for attempt in range(self._max_retries + 1):
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(operation),
                    timeout=self._timeout,
                )
            except Exception as exc:
                if attempt >= self._max_retries:
                    raise AIProviderError("Gemini request failed") from exc
                await asyncio.sleep((2**attempt) * 0.25 + random.uniform(0, 0.2))
        raise AIProviderError("Gemini request failed")

    async def describe_audio(self, audio: bytes) -> str:
        path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temporary:
                temporary.write(audio)
                path = Path(temporary.name)

            def describe() -> str:
                client = self._get_client()
                uploaded = client.files.upload(file=str(path))
                response = client.models.generate_content(
                    model=self._model,
                    contents=[AUDIO_DESCRIPTION_PROMPT_V1, uploaded],
                )
                return response.text or "No description found"

            return await self._retry(describe)
        finally:
            if path is not None:
                try:
                    os.unlink(path)
                except FileNotFoundError:
                    pass

    async def summarize_descriptions(self, descriptions: str) -> str:
        def summarize() -> str:
            response = self._get_client().models.generate_content(
                model=self._model,
                contents=[session_summary_prompt(descriptions)],
            )
            return response.text or "Error generating AI response, please try again!"

        return await self._retry(summarize)

    async def close(self) -> None:
        if self._client is not None:
            close = getattr(self._client, "close", None)
            if close is not None:
                await asyncio.to_thread(close)


def create_ai_provider(settings: Settings) -> AIProvider:
    if settings.ai_mode is AIMode.REMOTE:
        if not settings.ai_server_endpoint:
            return UnavailableAIProvider("AI_SERVER_ENDPOINT is not configured")
        return RemoteAIProvider(settings.ai_server_endpoint, settings.ai_timeout_seconds)
    if not settings.gemini_api_key:
        return UnavailableAIProvider("GEMINI_API_KEY is not configured")
    return GeminiAIProvider(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        timeout=settings.ai_timeout_seconds,
        max_retries=settings.ai_max_retries,
    )
