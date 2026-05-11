"""Minimal OpenTelemetry-compatible trace context.

Generates W3C trace-context headers (`traceparent`) and provides a
`traced` async/sync decorator that emits structured timing logs.

The context is propagated via `contextvars` so async tasks inherit it.
"""

from __future__ import annotations

import contextvars
import functools
import secrets
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, TypeVar

from core.observability.logger import get_logger
from core.observability.metrics import default_registry

_log = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


@dataclass(frozen=True, slots=True)
class TraceContext:
    trace_id: str
    span_id: str
    parent_span_id: str | None

    @property
    def traceparent(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-01"


_CURRENT: contextvars.ContextVar[TraceContext | None] = contextvars.ContextVar(
    "mspis_trace", default=None
)


def _new_trace_id() -> str:
    return secrets.token_hex(16)


def _new_span_id() -> str:
    return secrets.token_hex(8)


def current_trace() -> TraceContext | None:
    return _CURRENT.get()


@contextmanager
def span(name: str, **attrs: Any) -> Iterator[TraceContext]:
    parent = _CURRENT.get()
    trace_id = parent.trace_id if parent else _new_trace_id()
    new_ctx = TraceContext(
        trace_id=trace_id,
        span_id=_new_span_id(),
        parent_span_id=parent.span_id if parent else None,
    )
    token = _CURRENT.set(new_ctx)
    started = time.perf_counter()
    try:
        yield new_ctx
    except Exception as exc:
        default_registry.incr(f"span:{name}:error")
        _log.error("span_error", span=name, trace_id=new_ctx.trace_id, span_id=new_ctx.span_id,
                   error=str(exc), **attrs)
        raise
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        default_registry.observe(f"span:{name}:duration_ms", elapsed_ms)
        default_registry.incr(f"span:{name}:count")
        _log.debug("span_finished", span=name, trace_id=new_ctx.trace_id,
                   span_id=new_ctx.span_id, duration_ms=round(elapsed_ms, 3), **attrs)
        _CURRENT.reset(token)


def traced(name: str) -> Callable[[F], F]:
    """Decorate sync or async functions to time + log them."""

    def decorator(fn: F) -> F:
        import inspect
        if inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                with span(name):
                    return await fn(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            with span(name):
                return fn(*args, **kwargs)

        return sync_wrapper  # type: ignore[return-value]

    return decorator


__all__ = ["TraceContext", "current_trace", "span", "traced"]
