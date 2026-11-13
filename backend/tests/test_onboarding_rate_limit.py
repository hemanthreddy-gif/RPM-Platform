"""Public invitation and MFA bootstrap routes share authentication abuse controls."""

import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/auth/physician-invitations",
        "/api/v1/auth/physician-onboarding/start",
        "/api/v1/auth/physician-onboarding/complete",
    ],
)
def test_onboarding_rate_limit_rejects_before_processing(
    path: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def reject(**kwargs: object) -> bool:
        calls.append(str(kwargs["scope"]))
        return False

    monkeypatch.setattr(main._rate_limiter, "allowed", reject)
    response = TestClient(main.app).post(path, json={})
    assert response.status_code == 429
    assert response.headers["Cache-Control"] == "no-store"
    assert calls == ["auth"]
