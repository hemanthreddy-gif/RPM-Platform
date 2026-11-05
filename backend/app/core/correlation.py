"""Opaque correlation identifiers shared by API and durable-worker logs."""

from contextvars import ContextVar

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def set_request_id(value: str) -> None:
    """Store a validated opaque ID for the current request or worker event."""
    _request_id.set(value)


def current_request_id() -> str | None:
    """Return the request ID without manufacturing an identifier in domain code."""
    return _request_id.get()
