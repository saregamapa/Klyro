def test_change_password_wrong_current(client, auth_headers):
    r = client.patch(
        "/api/v1/users/me/password",
        json={"current_password": "WrongPass999", "new_password": "NewValid123"},
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_change_password_weak_new(client, auth_headers):
    r = client.patch(
        "/api/v1/users/me/password",
        json={"current_password": "TestPass123", "new_password": "weak"},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_export_data_returns_json(client, auth_headers):
    r = client.get("/api/v1/users/me/export", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "user" in data
    assert "chatbots" in data
    assert "conversations" in data
    assert "leads" in data


def test_delete_account(client):
    """Create a throwaway user and delete it."""
    import uuid

    email = f"del_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/v1/signup", json={"email": email, "password": "DelPass123"})
    tok = client.post(
        "/api/v1/login",
        json={"email": email, "password": "DelPass123"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}

    r = client.delete("/api/v1/users/me", headers=headers)
    assert r.status_code == 204

    r2 = client.get("/api/v1/users/me", headers=headers)
    assert r2.status_code == 401
