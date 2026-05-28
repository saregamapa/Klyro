from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-tests-only-not-prod")
os.environ.setdefault("DATABASE_PATH", ":memory:")
os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("EMAIL_ENABLED", "false")
os.environ.setdefault("STRIPE_SECRET_KEY", "")
os.environ.setdefault("ENVIRONMENT", "development")

from app.factory import create_app


@pytest.fixture(scope="session")
def app():
    application = create_app()
    application.state.limiter.enabled = False
    return application


@pytest.fixture(scope="session")
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers(client):
    """Register and log in a fresh test user, return auth headers."""
    import uuid

    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    pw = "TestPass123"
    client.post("/api/v1/signup", json={"email": email, "password": pw})
    r = client.post("/api/v1/login", json={"email": email, "password": pw})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
