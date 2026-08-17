import asyncio
import time
from dataclasses import dataclass, field


class AudioBufferError(ValueError):
    pass


class ChunkTooLargeError(AudioBufferError):
    pass


class BufferLimitError(AudioBufferError):
    pass


class ChunkOrderError(AudioBufferError):
    pass


@dataclass
class _SessionBuffer:
    data: bytearray = field(default_factory=bytearray)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    updated_at: float = field(default_factory=time.monotonic)
    expected_sequence: int = 0
    idempotency_keys: set[str] = field(default_factory=set)


class AudioBufferStore:
    def __init__(
        self,
        *,
        target_bytes: int,
        max_chunk_bytes: int,
        max_buffer_bytes: int,
        ttl_seconds: int,
        max_active_sessions: int,
    ) -> None:
        if target_bytes > max_buffer_bytes:
            raise ValueError("target_bytes cannot exceed max_buffer_bytes")
        self._target_bytes = target_bytes
        self._max_chunk_bytes = max_chunk_bytes
        self._max_buffer_bytes = max_buffer_bytes
        self._ttl_seconds = ttl_seconds
        self._max_active_sessions = max_active_sessions
        self._sessions: dict[int, _SessionBuffer] = {}
        self._store_lock = asyncio.Lock()

    async def _get_state(self, session_id: int) -> _SessionBuffer:
        async with self._store_lock:
            self._prune_expired()
            state = self._sessions.get(session_id)
            if state is None:
                if len(self._sessions) >= self._max_active_sessions:
                    raise BufferLimitError("Too many active audio sessions")
                state = _SessionBuffer()
                self._sessions[session_id] = state
            return state

    def _prune_expired(self) -> None:
        cutoff = time.monotonic() - self._ttl_seconds
        expired_sessions = [
            session_id
            for session_id, state in self._sessions.items()
            if state.updated_at < cutoff and not state.lock.locked()
        ]
        for session_id in expired_sessions:
            del self._sessions[session_id]

    async def append(
        self,
        session_id: int,
        chunk: bytes,
        *,
        sequence: int | None = None,
        idempotency_key: str | None = None,
    ) -> bytes | None:
        if len(chunk) > self._max_chunk_bytes:
            raise ChunkTooLargeError("Audio chunk exceeds configured maximum")

        state = await self._get_state(session_id)
        async with state.lock:
            if idempotency_key and idempotency_key in state.idempotency_keys:
                return None
            if sequence is not None and sequence != state.expected_sequence:
                raise ChunkOrderError(
                    f"Expected chunk sequence {state.expected_sequence}, received {sequence}"
                )
            if len(state.data) + len(chunk) > self._max_buffer_bytes:
                raise BufferLimitError("Session audio buffer exceeds configured maximum")

            state.data.extend(chunk)
            state.updated_at = time.monotonic()
            if sequence is not None:
                state.expected_sequence += 1
            if idempotency_key:
                state.idempotency_keys.add(idempotency_key)
                if len(state.idempotency_keys) > 1024:
                    state.idempotency_keys.pop()

            if len(state.data) < self._target_bytes:
                return None

            complete = bytes(state.data[: self._target_bytes])
            state.data.clear()
            state.expected_sequence = 0
            return complete

    async def active_session_count(self) -> int:
        async with self._store_lock:
            self._prune_expired()
            return len(self._sessions)
