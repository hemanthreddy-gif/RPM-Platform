"""The browser may call the authorized profile and consent mutation endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.parametrize("method", ["PATCH", "DELETE", "PUT"])
def test_profile_mutation_preflight_allows_configured_origin(method: str) -> None:
    response = TestClient(app).options(
        "/api/v1/patients/me",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    denied = TestClient(app).options(
        "/api/v1/patients/me",
        headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": method},
    )
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers
