from fastapi.testclient import TestClient

from app.ai.providers.fake import FakeProvider
from app.core.database import Base
from app.main import app


def test_health_exposes_fake_provider_and_request_id() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "ai_provider": "fake"}
    assert response.headers["X-Request-ID"]


def test_versioned_ping() -> None:
    response = TestClient(app).get("/api/v1/ping")

    assert response.status_code == 200
    assert response.json() == {"message": "pong"}


def test_foundation_metadata_and_fake_provider_are_offline() -> None:
    assert Base.metadata.naming_convention["pk"] == "pk_%(table_name)s"
    assert FakeProvider().is_available() is True
