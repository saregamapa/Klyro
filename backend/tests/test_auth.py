def test_signup_success(client):
    import uuid

    email = f"new_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/v1/signup",
        json={"email": email, "password": "NewPass123"},
    )
    assert r.status_code == 201
    assert r.json()["email"] == email


def test_signup_duplicate(client):
    data = {"email": "dup@example.com", "password": "DupPass123"}
    client.post("/api/v1/signup", json=data)
    r = client.post("/api/v1/signup", json=data)
    assert r.status_code == 409


def test_login_success(client):
    client.post(
        "/api/v1/signup",
        json={"email": "log@example.com", "password": "LogPass123"},
    )
    r = client.post(
        "/api/v1/login",
        json={"email": "log@example.com", "password": "LogPass123"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_wrong_password(client):
    client.post(
        "/api/v1/signup",
        json={"email": "wrong@example.com", "password": "WrongPass123"},
    )
    r = client.post(
        "/api/v1/login",
        json={"email": "wrong@example.com", "password": "BadPassword9"},
    )
    assert r.status_code == 401


def test_me_requires_auth(client):
    r = client.get("/api/v1/users/me")
    assert r.status_code == 401


def test_me_with_token(client, auth_headers):
    r = client.get("/api/v1/users/me", headers=auth_headers)
    assert r.status_code == 200
    assert "email" in r.json()


def test_forgot_password_no_leak(client):
    """Returns 204 even for non-existent emails (no enumeration)."""
    r = client.post(
        "/api/v1/forgot-password",
        json={"email": "nobody@example.com"},
    )
    assert r.status_code == 204


def test_password_reset_invalid_token(client):
    r = client.post(
        "/api/v1/reset-password",
        json={"token": "a" * 43, "new_password": "NewPass999"},
    )
    assert r.status_code == 400
