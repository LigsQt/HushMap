import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum, auto


class AudioBufferError(ValueError):
    pass


class ChunkTooLargeError(AudioBufferError):
    pass


class BufferLimitError(AudioBufferError):
    pass


class ChunkOrderError(AudioBufferError):
    pass


class AppendStatus(Enum):
    DUPLICATE_COMPLETED = auto()
    PROCESSING = auto()


@dataclass
class _SessionBuffer:
    owner_key: str
    data: bytearray = field(default_factory=bytearray)
    updated_at: float = field(default_factory=time.monotonic)
    expected_sequence: int = 0
    idempotency_keys: set[str] = field(default_factory=set)
    processing: bool = False


class AudioBufferStore:
    def __init__(
        self,
        *,
        target_bytes: int,
        max_chunk_bytes: int,
        max_buffer_bytes: int,
        ttl_seconds: int,
        max_active_sessions: int,
        max_active_sessions_per_owner: int | None = None,
        max_recent_idempotency_keys: int = 10_000,
    ) -> None:
        if target_bytes > max_buffer_bytes:
            raise ValueError("target_bytes cannot exceed max_buffer_bytes")
        if max_active_sessions_per_owner is not None and max_active_sessions_per_owner < 1:
            raise ValueError("max_active_sessions_per_owner must be positive")
        if max_recent_idempotency_keys < 1:
            raise ValueError("max_recent_idempotency_keys must be positive")
        self._target_bytes = target_bytes
        self._max_chunk_bytes = max_chunk_bytes
        self._max_buffer_bytes = max_buffer_bytes
        self._ttl_seconds = ttl_seconds
        self._max_active_sessions = max_active_sessions
        self._max_active_sessions_per_owner = (
            max_active_sessions
            if max_active_sessions_per_owner is None
            else min(max_active_sessions_per_owner, max_active_sessions)
        )
        self._max_recent_idempotency_keys = max_recent_idempotency_keys
        self._sessions: dict[int, _SessionBuffer] = {}
        self._recent_idempotency_keys: dict[tuple[str, int, str], float] = {}
        self._store_lock = asyncio.Lock()

    def _get_state(self, session_id: int, owner_key: str) -> _SessionBuffer:
        self._prune_expired()
        state = self._sessions.get(session_id)
        if state is not None:
            if state.owner_key != owner_key:
                raise BufferLimitError("Audio session is active for another device")
            return state

        if len(self._sessions) >= self._max_active_sessions:
            raise BufferLimitError("Too many active audio sessions")
        owner_session_count = sum(
            existing.owner_key == owner_key for existing in self._sessions.values()
        )
        if owner_session_count >= self._max_active_sessions_per_owner:
            raise BufferLimitError("Device has too many active audio sessions")

        state = _SessionBuffer(owner_key=owner_key)
        self._sessions[session_id] = state
        return state

    def _prune_expired(self) -> None:
        now = time.monotonic()
        cutoff = now - self._ttl_seconds
        expired_sessions = [
            session_id
            for session_id, state in self._sessions.items()
            if state.updated_at < cutoff and not state.processing
        ]
        for session_id in expired_sessions:
            del self._sessions[session_id]
        expired_keys = [
            key
            for key, accepted_at in self._recent_idempotency_keys.items()
            if accepted_at < cutoff
        ]
        for key in expired_keys:
            del self._recent_idempotency_keys[key]

    async def is_completed_duplicate(
        self,
        session_id: int,
        idempotency_key: str,
        owner_key: str,
    ) -> bool:
        async with self._store_lock:
            self._prune_expired()
            return (
                owner_key,
                session_id,
                idempotency_key,
            ) in self._recent_idempotency_keys

    async def append(
        self,
        session_id: int,
        chunk: bytes,
        *,
        sequence: int | None = None,
        idempotency_key: str | None = None,
        owner_key: str = "default",
    ) -> bytes | None | AppendStatus:
        if len(chunk) > self._max_chunk_bytes:
            raise ChunkTooLargeError("Audio chunk exceeds configured maximum")

        async with self._store_lock:
            self._prune_expired()
            completed_key = (
                (owner_key, session_id, idempotency_key) if idempotency_key else None
            )
            if (
                completed_key is not None
                and completed_key in self._recent_idempotency_keys
            ):
                return AppendStatus.DUPLICATE_COMPLETED

            state = self._get_state(session_id, owner_key)
            if state.processing:
                return AppendStatus.PROCESSING
            if idempotency_key and idempotency_key in state.idempotency_keys:
                if len(state.data) >= self._target_bytes:
                    state.processing = True
                    state.updated_at = time.monotonic()
                    return bytes(state.data[: self._target_bytes])
                return None
            if sequence is not None and sequence != state.expected_sequence:
                if not state.data:
                    del self._sessions[session_id]
                raise ChunkOrderError(
                    f"Expected chunk sequence {state.expected_sequence}, received {sequence}"
                )
            if len(state.data) + len(chunk) > self._max_buffer_bytes:
                if not state.data:
                    del self._sessions[session_id]
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
            state.processing = True
            return complete

    async def finalize_completion(self, session_id: int, owner_key: str) -> None:
        async with self._store_lock:
            state = self._sessions.get(session_id)
            if state is None or state.owner_key != owner_key or not state.processing:
                raise AudioBufferError("Audio completion state is unavailable")

            accepted_at = time.monotonic()
            for key in state.idempotency_keys:
                self._recent_idempotency_keys[(owner_key, session_id, key)] = accepted_at
            overflow = len(self._recent_idempotency_keys) - self._max_recent_idempotency_keys
            for key in list(self._recent_idempotency_keys)[: max(overflow, 0)]:
                del self._recent_idempotency_keys[key]
            del self._sessions[session_id]

    async def abort_completion(self, session_id: int, owner_key: str) -> None:
        async with self._store_lock:
            state = self._sessions.get(session_id)
            if state is not None and state.owner_key == owner_key:
                state.processing = False
                state.updated_at = time.monotonic()

    async def active_session_count(self) -> int:
        async with self._store_lock:
            self._prune_expired()
            return len(self._sessions)
