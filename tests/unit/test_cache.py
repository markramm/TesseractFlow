"""Unit tests for evaluation caching utilities."""
from __future__ import annotations

from pathlib import Path

import pytest

from tesseract_flow.core.exceptions import CacheError
from tesseract_flow.evaluation.cache import FileCacheBackend, build_cache_key


def test_build_cache_key_is_deterministic() -> None:
    key_one = build_cache_key("prompt", "model", 0.1234567)
    key_two = build_cache_key("prompt", "model", 0.1234567)
    assert key_one == key_two


def test_build_cache_key_changes_with_input() -> None:
    base = build_cache_key("prompt", "model", 0.1)
    assert base != build_cache_key("prompt!", "model", 0.1)
    assert base != build_cache_key("prompt", "other-model", 0.1)
    assert base != build_cache_key("prompt", "model", 0.2)


def test_file_cache_backend_round_trip(tmp_path: Path) -> None:
    backend = FileCacheBackend(tmp_path)
    key = "abc123"
    assert backend.get(key) is None
    backend.set(key, "{\"value\": 1}")
    assert backend.get(key) == "{\"value\": 1}"
    backend.clear()
    assert backend.get(key) is None


def test_file_cache_backend_rejects_empty_key(tmp_path: Path) -> None:
    backend = FileCacheBackend(tmp_path)
    with pytest.raises(CacheError):
        backend.get("   ")  # type: ignore[arg-type]
