"""Hosted previews fail closed while local synthetic workflows remain available."""

from collections.abc import Coroutine
from importlib import import_module
from secrets import token_urlsafe

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings
from app.core.security import SlidingWindowRateLimiter

main_module = import_module("app.main")
GATEWAY_SECRET = token_urlsafe(48)


def hosted_settings() -> dict[str, object]:
    return {
        "hosted_demo": True,
        "ai_provider": "fake",
        "synthetic_demo_rules_enabled": True,
        "jwt_secret": token_urlsafe(48),
        "backend_gateway_secret": GATEWAY_SECRET,
        "trusted_admin_provisioning_key": token_urlsafe(48),
        "mfa_encryption_key": Fernet.generate_key().decode(),
        "s3_access_key_id": token_urlsafe(24),
        "s3_secret_access_key": token_urlsafe(48),
        "database_url": f"postgresql+psycopg://preview_runtime:{token_urlsafe(32)}@db.internal/preview",
        "cors_allowed_origins": "https://preview.example.com",
    }


def test_safe_hosted_configuration_and_local_defaults_are_accepted() -> None:
    assert Settings(_env_file=None, **hosted_settings()).hosted_demo
    assert Settings(_env_file=None).hosted_demo is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("ai_provider", "remote"),
        ("synthetic_demo_rules_enabled", False),
        ("jwt_secret", "development-only-change-me-before-any-deployment"),
        ("jwt_secret", "too-short"),
        ("backend_gateway_secret", ""),
        ("backend_gateway_secret", "short"),
        ("trusted_admin_provisioning_key", "development-only-admin-provisioning-key"),
        ("mfa_encryption_key", "OQ9tNSZpc8hWNgeFU_U8zVgKIkp-RAlQEob4cWKo_6g="),
        ("mfa_encryption_key", "invalid"),
        ("database_url", "postgresql+psycopg://rpm:development-only-change-me@db.internal/rpm"),
        ("database_url", "postgresql+psycopg://rpm@db.internal/rpm"),
        ("database_url", "sqlite:///preview.db"),
        ("s3_access_key_id", "rpm-local-development-only"),
        ("s3_secret_access_key", "development-only-change-me"),
        ("cors_allowed_origins", "http://preview.example.com"),
        ("cors_allowed_origins", "*"),
        ("cors_allowed_origins", "https://*.example.com"),
        ("cors_allowed_origins", "https://preview.example.com/path"),
        ("cors_allowed_origins", "https://user:password@preview.example.com"),
        ("cors_allowed_origins", ""),
    ],
)
def test_hosted_configuration_rejects_unsafe_values(field: str, value: object) -> None:
    settings = hosted_settings()
    settings[field] = value
    with pytest.raises(ValidationError) as failure:
        Settings(_env_file=None, **settings)
    # Startup failures must not dump the settings dictionary and its credentials.
    assert str(settings["jwt_secret"]) not in str(failure.value)
    assert str(settings["s3_secret_access_key"]) not in str(failure.value)


def request(path: str, method: str = "POST", gateway: str = GATEWAY_SECRET) -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "scheme": "https",
            "path": path,
            "query_string": b"",
            "headers": [(b"x-demo-gateway-key", gateway.encode())] if gateway else [],
            "client": ("198.51.100.42", 1234),
            "server": ("preview.example.com", 443),
        }
    )


def finish(coroutine: Coroutine[object, object, Response]) -> Response:
    # These middleware unit tests do no asynchronous I/O. Driving the coroutine directly
    # avoids requiring the Windows sandbox to create event-loop networking handles.
    try:
        coroutine.send(None)
    except StopIteration as result:
        return result.value
    finally:
        coroutine.close()
    raise AssertionError("Unexpected asynchronous I/O in middleware unit test")


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/auth/provision",
        "/api/v1/auth/provision/",
        "/api/v1/auth/physician-invitations",
        "/api/v1/auth/physician-invitations/",
        "/api/v1/admin",
        "/api/v1/admin/assignments",
        "/api/v1/admin/future-endpoint",
    ],
)
@pytest.mark.parametrize("method", ["POST", "GET", "OPTIONS"])
def test_hosted_admin_paths_are_denied_before_auth_or_database_work(
    path: str, method: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(main_module, "settings", Settings(_env_file=None, **hosted_settings()))

    async def forbidden_handler(_: Request) -> Response:
        raise AssertionError("Hosted administrative request reached router/database dependencies")

    response = finish(main_module.request_id_middleware(request(path, method), forbidden_handler))
    assert response.status_code == 403
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/physician-onboarding/start",
        "/api/v1/auth/physician-onboarding/complete",
    ],
)
def test_hosted_patient_registration_and_invitation_redemption_remain_available(
    path: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(main_module, "settings", Settings(_env_file=None, **hosted_settings()))
    monkeypatch.setattr(main_module, "_rate_limiter", SlidingWindowRateLimiter())

    async def handler(_: Request) -> Response:
        return Response(status_code=204)

    response = finish(main_module.request_id_middleware(request(path), handler))
    assert response.status_code == 204


def test_local_operator_provisioning_is_not_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main_module, "settings", Settings(_env_file=None))
    monkeypatch.setattr(main_module, "_rate_limiter", SlidingWindowRateLimiter())

    async def handler(_: Request) -> Response:
        return Response(status_code=204)

    response = finish(
        main_module.request_id_middleware(request("/api/v1/auth/physician-invitations"), handler)
    )
    assert response.status_code == 204


@pytest.mark.parametrize("gateway", ["", "incorrect", "é" * 40])
@pytest.mark.parametrize("path", ["/api/v1/auth/register", "/api/v1/patients/me", "/ready"])
def test_hosted_requests_require_private_gateway_key(
    gateway: str, path: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(main_module, "settings", Settings(_env_file=None, **hosted_settings()))

    async def forbidden_handler(_: Request) -> Response:
        raise AssertionError("Untrusted request reached router/database dependencies")

    response = finish(
        main_module.request_id_middleware(request(path, gateway=gateway), forbidden_handler)
    )
    assert response.status_code == 403


def test_hosted_health_remains_available_without_gateway_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main_module, "settings", Settings(_env_file=None, **hosted_settings()))

    async def handler(_: Request) -> Response:
        return Response(status_code=200)

    response = finish(
        main_module.request_id_middleware(request("/health", "GET", gateway=""), handler)
    )
    assert response.status_code == 200
