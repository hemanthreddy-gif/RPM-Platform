"""Phase 0 FastAPI application entrypoint."""

from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from time import monotonic
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.modules.alerts.router import router as alerts_router
from app.modules.identity.router import router as identity_router
from app.modules.medications.router import router as medications_router
from app.modules.observations.router import router as observations_router
from app.modules.patients.router import router as patients_router

configure_logging()
settings = get_settings()
logger = structlog.get_logger(__name__)

app = FastAPI(title="RPM Platform API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Provisioning-Key"],
)
app.include_router(identity_router)
app.include_router(patients_router)
app.include_router(observations_router)
app.include_router(alerts_router)
app.include_router(medications_router)

_auth_attempts: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def request_id_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Add an opaque request id and log only route/status metadata."""
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    if request.url.path in {"/api/v1/auth/login", "/api/v1/auth/password-reset"}:
        source = request.client.host if request.client else "unknown"
        attempts = _auth_attempts[source]
        cutoff = monotonic() - 60
        while attempts and attempts[0] < cutoff:
            attempts.popleft()
        if len(attempts) >= 10:
            return JSONResponse(status_code=429, content={"detail": "Too many requests"})
        attempts.append(monotonic())
    with structlog.contextvars.bound_contextvars(request_id=request_id):
        response = await call_next(request)
        logger.info(
            "request.completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
        )
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health", tags=["system"])
async def health() -> JSONResponse:
    """Liveness endpoint; dependency readiness is added only when dependencies exist."""
    return JSONResponse({"status": "ok", "ai_provider": settings.ai_provider})


@app.get("/api/v1/ping", tags=["system"])
async def ping() -> dict[str, str]:
    """Versioned API reachability endpoint."""
    return {"message": "pong"}
