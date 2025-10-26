"""Response caching utilities for evaluation workflows."""
from __future__ import annotations

import contextlib
import json
import os
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from tesseract_flow.core.exceptions import CacheError


@runtime_checkable
class CacheBackend(Protocol):
    """Protocol describing the evaluation response cache contract."""

    def get(self, key: str) -> Optional[str]:
        """Return cached payload for *key* if present, otherwise ``None``."""

    def set(self, key: str, value: str) -> None:
        """Persist ``value`` for *key* so future lookups return the payload."""

    def clear(self) -> None:
        """Remove all cached payloads managed by the backend."""


def build_cache_key(prompt: str, model: str, temperature: float) -> str:
    """Return a deterministic cache key for the evaluator request payload."""

    fingerprint = {
        "prompt": prompt,
        "model": model,
        "temperature": round(float(temperature), 6),
    }
    serialized = json.dumps(fingerprint, sort_keys=True, separators=(",", ":"))
    return sha256(serialized.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class FileCacheBackend:
    """Filesystem-backed cache storing one JSON file per request hash."""

    cache_dir: Path
    encoding: str = "utf-8"

    def __post_init__(self) -> None:
        self.cache_dir = Path(self.cache_dir)
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:  # pragma: no cover - defensive guard
            msg = f"Failed to initialize cache directory '{self.cache_dir}'."
            raise CacheError(msg) from exc

    def get(self, key: str) -> Optional[str]:
        path = self._path_for_key(key)
        try:
            with path.open("r", encoding=self.encoding) as handle:
                return handle.read()
        except FileNotFoundError:
            return None
        except OSError as exc:  # pragma: no cover - defensive guard
            msg = f"Failed to read cache entry '{key}'."
            raise CacheError(msg) from exc

    def set(self, key: str, value: str) -> None:
        path = self._path_for_key(key)
        tmp_path = path.with_suffix(".tmp")
        try:
            with tmp_path.open("w", encoding=self.encoding) as handle:
                handle.write(value)
            os.replace(tmp_path, path)
        except OSError as exc:  # pragma: no cover - defensive guard
            msg = f"Failed to write cache entry '{key}'."
            raise CacheError(msg) from exc
        finally:
            with contextlib.suppress(FileNotFoundError):
                tmp_path.unlink()

    def clear(self) -> None:
        try:
            for item in self.cache_dir.glob("*.json"):
                item.unlink(missing_ok=True)
        except OSError as exc:  # pragma: no cover - defensive guard
            msg = f"Failed to clear cache directory '{self.cache_dir}'."
            raise CacheError(msg) from exc

    def _path_for_key(self, key: str) -> Path:
        safe_key = key.strip()
        if not safe_key:
            msg = "Cache key must be a non-empty string."
            raise CacheError(msg)
        return self.cache_dir / f"{safe_key}.json"

