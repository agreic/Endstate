"""
Opik client wrapper.
Provides safe no-op behavior when Opik is not installed.
"""
from __future__ import annotations

from typing import Any


try:
    import opik
except Exception:  # pragma: no cover - optional dependency
    opik = None


def log_metric(name: str, value: float, session_id: str | None = None, tags: list[str] | None = None) -> None:
    if opik is None:
        return
    payload: dict[str, Any] = {"name": name, "value": value}
    if session_id:
        payload["session_id"] = session_id
    if tags:
        payload["tags"] = tags
    opik.log_metric(**payload)
