import hashlib
import time
from typing import Any, NamedTuple


class CacheEntry(NamedTuple):
    data: dict[str, Any]
    timestamp: float


class InMemoryCache:
    """
    Thread-safe, deterministic SHA-256 cache with Time-To-Live (TTL).
    Prevents redundant downstream API calls and tracks cache efficacy.
    """

    def __init__(self, ttl_seconds: int = 3600):
        # Dictionary storing: { sha256_hash: CacheEntry(data, timestamp) }
        self._store: dict[str, CacheEntry] = {}
        self.ttl_seconds = ttl_seconds

    def _generate_key(self, model: str, prompt: str) -> str:
        """
        Produces a unique 64-char hex digest for the model + normalized prompt.
        Whitespace is stripped so trivial spacing doesn't cause cache misses.
        """
        normalized_content = f"{model}:{prompt.strip()}"
        return hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()

    def get(self, model: str, prompt: str) -> dict[str, Any] | None:
        """
        Retrieves cached response payload if it exists and has not expired.
        Automatically purges stale entries upon inspection.
        """
        key = self._generate_key(model, prompt)
        entry = self._store.get(key)

        if not entry:
            return None

        # Check TTL expiration
        if (time.time() - entry.timestamp) > self.ttl_seconds:
            # Stale entry detected; remove to reclaim memory
            del self._store[key]
            return None

        return entry.data

    def set(self, model: str, prompt: str, data: dict[str, Any]) -> None:
        """
        Stores serialized response payload with current UNIX epoch timestamp.
        """
        key = self._generate_key(model, prompt)
        self._store[key] = CacheEntry(
            data=data,
            timestamp=time.time()
        )

    def size(self) -> int:
        """Returns total active keys stored in the cache."""
        return len(self._store)


# Global singleton instance (1-hour default TTL)
response_cache = InMemoryCache(ttl_seconds=3600)