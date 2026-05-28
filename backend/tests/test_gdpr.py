def test_forgot_password_always_204(client):
    """No user enumeration — unknown email still returns 204."""
    r = client.post(
        "/api/v1/forgot-password",
        json={"email": "unknown@example.com"},
    )
    assert r.status_code == 204


def test_export_requires_auth(client):
    r = client.get("/api/v1/users/me/export")
    assert r.status_code == 401


def test_delete_requires_auth(client):
    r = client.delete("/api/v1/users/me")
    assert r.status_code == 401
