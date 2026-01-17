"""
Gmail RLM Caching Layer

This module provides a disk-based caching layer for RLM LLM queries.
Caching reduces costs by avoiding redundant API calls for identical prompts.

Features:
- SHA256-based cache keys from prompt+context+model
- TTL-based expiration (default: 24 hours)
- Cache stats (hits, misses, tokens saved)
- JSON file storage in temp directory
"""

import hashlib
import json
import tempfile
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


@dataclass
class CacheEntry:
    """Represents a cached LLM query result."""
    result: str
    created_at: str
    tokens_saved: int
    model: str
    prompt_hash: str  # For debugging/verification


class QueryCache:
    """
    Disk-based cache for LLM query results.

    Uses SHA256 hashing of prompt+context+model to create cache keys.
    Entries expire after ttl_hours (default: 24).

    Usage:
        cache = QueryCache()
        key = cache.get_key(prompt, context, model)

        # Check cache
        if result := cache.get(key):
            return result

        # ... make API call ...

        # Store result
        cache.set(key, result, tokens_used, model)
    """

    def __init__(self, cache_dir: str = None, ttl_hours: int = 24):
        """
        Initialize the cache.

        Args:
            cache_dir: Directory for cache files (default: temp dir)
            ttl_hours: Time-to-live in hours (default: 24)
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(tempfile.gettempdir()) / "rlm_cache"

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_hours = ttl_hours
        self.hits = 0
        self.misses = 0
        self.tokens_saved = 0

    def get_key(self, prompt: str, context: str, model: str) -> str:
        """
        Generate a cache key from prompt, context, and model.

        Args:
            prompt: The LLM prompt
            context: The context data
            model: The model name

        Returns:
            SHA256 hash string
        """
        content = f"{prompt}|{context}|{model}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_cache_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        return self.cache_dir / f"{key}.json"

    def get(self, key: str) -> Optional[str]:
        """
        Retrieve a cached result if exists and not expired.

        Args:
            key: Cache key from get_key()

        Returns:
            Cached result string, or None if not found/expired
        """
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            data = json.loads(cache_path.read_text())
            entry = CacheEntry(**data)

            # Check expiration
            created = datetime.fromisoformat(entry.created_at)
            if datetime.now() - created > timedelta(hours=self.ttl_hours):
                # Expired - remove and return None
                cache_path.unlink(missing_ok=True)
                return None

            # Valid cache hit
            self.hits += 1
            self.tokens_saved += entry.tokens_saved
            return entry.result

        except (json.JSONDecodeError, TypeError, KeyError):
            # Corrupted cache file
            cache_path.unlink(missing_ok=True)
            return None

    def set(self, key: str, result: str, tokens: int, model: str) -> None:
        """
        Store a result in the cache.

        Args:
            key: Cache key from get_key()
            result: LLM response to cache
            tokens: Total tokens used (for stats)
            model: Model name (for verification)
        """
        entry = CacheEntry(
            result=result,
            created_at=datetime.now().isoformat(),
            tokens_saved=tokens,
            model=model,
            prompt_hash=key[:16]  # Store partial hash for debugging
        )

        cache_path = self._get_cache_path(key)
        cache_path.write_text(json.dumps(asdict(entry), indent=2))

    def stats(self) -> dict:
        """
        Return cache statistics.

        Returns:
            Dict with hits, misses, hit_rate, tokens_saved
        """
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0.0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 3),
            "tokens_saved": self.tokens_saved
        }

    def clear(self) -> int:
        """
        Clear all cached entries.

        Returns:
            Number of entries cleared
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
            count += 1
        return count

    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                data = json.loads(cache_file.read_text())
                created = datetime.fromisoformat(data.get("created_at", ""))
                if datetime.now() - created > timedelta(hours=self.ttl_hours):
                    cache_file.unlink()
                    count += 1
            except (json.JSONDecodeError, ValueError):
                cache_file.unlink()
                count += 1
        return count


# Global cache instance
_cache: Optional[QueryCache] = None


def get_cache() -> Optional[QueryCache]:
    """Get the global cache instance."""
    return _cache


def init_cache(cache_dir: str = None, ttl_hours: int = 24) -> QueryCache:
    """Initialize or reset the global cache."""
    global _cache
    _cache = QueryCache(cache_dir=cache_dir, ttl_hours=ttl_hours)
    return _cache


def disable_cache() -> None:
    """Disable caching by setting global cache to None."""
    global _cache
    _cache = None
