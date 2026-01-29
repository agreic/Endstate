"""
Opik client wrapper.
Provides safe no-op behavior when Opik is not installed.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator


try:
    import opik # type: ignore
except Exception:  # pragma: no cover
    opik = None


def _project_name() -> str:
    return os.getenv("OPIK_PROJECT", "endstate-demo")

def log_metric(
    name: str,
    value: float,
    session_id: str | None = None,
    tags: list[str] | None = None,
) -> None:
    """
    Best-effort metric logging.
    Different Opik SDK versions expose different APIs.
    This must never crash the app.
    """
    if opik is None:
        return

    payload: dict[str, Any] = {"name": name, "value": value}
    if session_id:
        payload["session_id"] = session_id
    if tags:
        payload["tags"] = tags

    try:
        fn = getattr(opik, "log_metric", None)
        if callable(fn):
            fn(**payload)
            return

        # fallback: attach metrics to current trace if possible
        current = getattr(opik, "current_trace", None)
        if callable(current):
            t = current()
            if t is not None:
                metrics = getattr(t, "metrics", None)
                if isinstance(metrics, dict):
                    metrics[name] = value
                    return
                setattr(t, "metrics", {name: value})
                return
    except Exception:
        return



@contextmanager
def trace(
    name: str,
    input: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> Iterator[Any]:
    if opik is None:
        yield None
        return

    kwargs: dict[str, Any] = {"name": name, "project_name": _project_name()}
    if tags:
        kwargs["tags"] = tags

    with opik.start_as_current_trace(**kwargs) as t:
        if input is not None:
            t.input = input
        if metadata is not None:
            t.metadata = metadata
        yield t

@contextmanager
def span(
    name: str,
    metadata: dict[str, Any] | None = None,
) -> Iterator[Any]:
    if opik is None:
        yield None
        return

    with opik.start_as_current_span(name=name) as s:
        if metadata is not None:
            s.metadata = metadata
        yield s

