"""Phase 0 FastAPI application entrypoint."""

from collections.abc import Awaitable, Callable
from hashlib import sha256
from uuid import UUID, uuid4

import redis
import structlog
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.correlation import set_request_id
from app.core.database import engine
from app.core.logging import configure_logging
from app.core.security import SlidingWindowRateLimiter
from app.modules.alerts.router import router as alerts_router
from app.modules.devices.router import router as devices_router
from app.modules.fhir.router import router as fhir_router
from app.modules.identity.router import router as identity_router
from app.modules.insights.router import router as insights_router
from app.modules.medications.router import router as medications_router
from app.modules.messaging.router import router as messaging_router
from app.modules.nutrition.router import router as nutrition_router
from app.modules.observations.router import router as observations_router
from app.modules.patients.router import router as patients_router

configure_logging()
settings = get_settings()
logger = structlog.get_logger(__name__)

app = FastAPI(title="RPM Platform API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Idempotency-Key",
        "X-Request-ID",
        "X-Provisioning-Key",
    ],
)
app.include_router(identity_router)
app.include_router(devices_router)
app.include_router(fhir_router)
app.include_router(insights_router)
app.include_router(patients_router)
app.include_router(observations_router)
app.include_router(alerts_router)
app.include_router(medications_router)
app.include_router(messaging_router)
app.include_router(nutrition_router)

_rate_limiter = SlidingWindowRateLimiter()
_RATE_LIMITED_ROUTES = {
    "/api/v1/auth/register": "auth",
    "/api/v1/auth/login": "auth",
    "/api/v1/auth/refresh": "auth",
    "/api/v1/auth/logout": "auth",
    "/api/v1/auth/mfa/enroll": "auth",
    "/api/v1/auth/mfa/verify": "auth",
    "/api/v1/auth/password-reset": "auth",
    "/api/v1/auth/password-reset/confirm": "auth",
    "/api/v1/auth/provision": "auth",
    "/api/v1/observations": "ingestion",
}


def apply_api_response_protections(response: Response, request_id: str) -> Response:
    """Attach response protections after application code has completed successfully."""
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), geolocation=(), microphone=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
    )
    response.headers["Cache-Control"] = "no-store"
    return response


def readiness_status(
    database_probe: Callable[[], None], redis_probe: Callable[[], None]
) -> tuple[bool, dict[str, str]]:
    """Evaluate dependency probes without converting an outage into a healthy response."""
    dependencies: dict[str, str] = {}
    for name, probe in (("database", database_probe), ("redis", redis_probe)):
        try:
            probe()
            dependencies[name] = "ok"
        except Exception:  # noqa: BLE001 - readiness intentionally reduces provider failures to status.
            dependencies[name] = "unavailable"
    return all(value == "ok" for value in dependencies.values()), dependencies


def _database_ready() -> None:
    with engine.connect() as connection:
        connection.exec_driver_sql("SELECT 1")


def _redis_ready() -> None:
    client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
    try:
        client.ping()
    finally:
        client.close()


@app.middleware("http")
async def request_id_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Add an opaque request id and log only route/status metadata."""
    try:
        request_id = (
            str(uuid4())
            if "X-Request-ID" not in request.headers
            else str(UUID(request.headers["X-Request-ID"]))
        )
    except ValueError:
        request_id = str(uuid4())
    scope = _RATE_LIMITED_ROUTES.get(request.url.path)
    if request.url.path.startswith("/api/v1/devices/") and request.url.path.endswith("/readings"):
        scope = "ingestion"
    is_preflight = (
        request.method == "OPTIONS" and "Access-Control-Request-Method" in request.headers
    )
    if scope is not None and not is_preflight:
        if scope == "ingestion":
            credential = request.headers.get("Authorization") or request.headers.get(
                "X-Device-Token"
            )
            source = (
                sha256(credential.encode()).hexdigest() if credential else "anonymous-ingestion"
            )
        else:
            source = request.client.host if request.client else "unknown"
        limit = (
            settings.auth_rate_limit_per_minute
            if scope == "auth"
            else settings.ingestion_rate_limit_per_minute
        )
        if not _rate_limiter.allowed(scope=scope, source=source, limit=limit, window_seconds=60):
            return apply_api_response_protections(
                JSONResponse(status_code=429, content={"detail": "Too many requests"}), request_id
            )
    set_request_id(request_id)
    with structlog.contextvars.bound_contextvars(request_id=request_id):
        response = await call_next(request)
        logger.info(
            "request.completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
        )
    return apply_api_response_protections(response, request_id)


@app.get("/health", tags=["system"])
async def health() -> JSONResponse:
    """Liveness endpoint; it intentionally does not depend on external services."""
    return JSONResponse({"status": "ok", "ai_provider": settings.ai_provider})


@app.get("/ready", tags=["system"])
async def ready() -> JSONResponse:
    """Expose database and broker readiness without hiding a dependency outage."""
    ready_now, dependencies = readiness_status(_database_ready, _redis_ready)
    return JSONResponse(
        {"status": "ready" if ready_now else "not_ready", "dependencies": dependencies},
        status_code=status.HTTP_200_OK if ready_now else status.HTTP_503_SERVICE_UNAVAILABLE,
    )


@app.get("/api/v1/ping", tags=["system"])
async def ping() -> dict[str, str]:
    """Versioned API reachability endpoint."""
    return {"message": "pong"}
