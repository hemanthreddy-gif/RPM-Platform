"""Focused Phase 10 security and graceful-degradation regressions."""

from datetime import UTC, datetime, timedelta
from importlib import import_module
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.responses import Response

from app.core.config import Settings
from app.core.security import SlidingWindowRateLimiter
from app.modules.identity.router import current_principal

main_module = import_module("app.main")


def test_api_applies_strict_response_protections_and_safe_correlation_id() -> None:
    response = main_module.apply_api_response_protections(Response(), "safe-request-id")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Request-ID"] == "safe-request-id"


def test_rate_limiter_blocks_only_after_its_scoped_window_is_exhausted() -> None:
    limiter = SlidingWindowRateLimiter()

    assert limiter.allowed(scope="auth", source="198.51.100.1", limit=2, window_seconds=60)
    assert limiter.allowed(scope="auth", source="198.51.100.1", limit=2, window_seconds=60)
    assert not limiter.allowed(scope="auth", source="198.51.100.1", limit=2, window_seconds=60)
    assert limiter.allowed(scope="ingestion", source="198.51.100.1", limit=2, window_seconds=60)


def test_cors_configuration_refuses_a_wildcard_origin() -> None:
    settings = Settings(cors_allowed_origins="*")

    try:
        _ = settings.cors_origins
    except ValueError as error:
        assert "explicit allow-list" in str(error)
    else:
        raise AssertionError("Wildcard CORS configuration must not be accepted")


def test_readiness_reports_dependency_failure_visibly() -> None:
    def unavailable() -> None:
        raise RuntimeError("dependency unavailable")

    ready, dependencies = main_module.readiness_status(unavailable, unavailable)

    assert ready is False
    assert dependencies == {"database": "unavailable", "redis": "unavailable"}


def test_access_token_invalidation_epoch_rejects_a_previously_issued_token() -> None:
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "role": "patient",
            "mfa": False,
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        Settings().jwt_secret,
        algorithm="HS256",
    )

    class Result:
        def scalar_one_or_none(self) -> datetime:
            return now + timedelta(seconds=1)

    class Session:
        def execute(self, *args: object, **kwargs: object) -> Result:
            return Result()

    with pytest.raises(HTTPException, match="revoked"):
        current_principal(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
            Session(),  # type: ignore[arg-type]
        )


def test_cors_preflight_does_not_consume_auth_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    from starlette.requests import Request

    monkeypatch.setattr(main_module, "_rate_limiter", SlidingWindowRateLimiter())
    monkeypatch.setattr(main_module.settings, "auth_rate_limit_per_minute", 1)

    def request(method: str, headers: list[tuple[bytes, bytes]]) -> Request:
        return Request(
            {
                "type": "http",
                "method": method,
                "scheme": "http",
                "path": "/api/v1/auth/login",
                "query_string": b"",
                "headers": headers,
                "client": ("test", 1),
                "server": ("test", 80),
            }
        )

    async def next_handler(_: Request) -> Response:
        return Response(status_code=204)

    async def exercise() -> None:
        preflight = request(
            "OPTIONS",
            [(b"origin", b"http://localhost:3000"), (b"access-control-request-method", b"POST")],
        )
        assert (await main_module.request_id_middleware(preflight, next_handler)).status_code == 204
        assert (
            await main_module.request_id_middleware(request("POST", []), next_handler)
        ).status_code == 204
        assert (
            await main_module.request_id_middleware(request("POST", []), next_handler)
        ).status_code == 429

    asyncio.run(exercise())


def test_celery_registers_all_scheduled_task_modules() -> None:
    from app.workers.celery_app import celery_app

    celery_app.loader.import_default_modules()
    scheduled = {entry["task"] for entry in celery_app.conf.beat_schedule.values()}
    assert scheduled <= set(celery_app.tasks)
