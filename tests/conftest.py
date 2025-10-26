"""Pytest configuration for test suite."""
from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_configure(config) -> None:  # pragma: no cover - pytest hook
    config.addinivalue_line("markers", "asyncio: mark test as requiring asyncio event loop")


def pytest_pyfunc_call(pyfuncitem):  # pragma: no cover - pytest hook
    if asyncio.iscoroutinefunction(pyfuncitem.obj):
        loop = asyncio.new_event_loop()
        try:
            signature = inspect.signature(pyfuncitem.obj)
            kwargs = {
                name: pyfuncitem.funcargs[name]
                for name in signature.parameters
                if name in pyfuncitem.funcargs
            }
            loop.run_until_complete(pyfuncitem.obj(**kwargs))
        finally:
            loop.close()
        return True
    return None
