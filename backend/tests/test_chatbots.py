def test_create_chatbot(client, auth_headers):
    r = client.post(
        "/api/v1/chatbots",
        json={"name": "TestBot", "website_url": "https://example.com"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    assert r.json()["name"] == "TestBot"


def test_chatbot_quota_free_plan(client, auth_headers):
    """Free plan: 1 chatbot. Second creation should return 402."""
    client.post(
        "/api/v1/chatbots",
        json={"name": "Bot1", "website_url": "https://example.com"},
        headers=auth_headers,
    )
    r = client.post(
        "/api/v1/chatbots",
        json={"name": "Bot2", "website_url": "https://example.com"},
        headers=auth_headers,
    )
    assert r.status_code == 402


def test_cross_tenant_returns_404(client, auth_headers):
    """Other user cannot read a chatbot owned by someone else — must be 404 not 403."""
    import uuid

    email2 = f"t2_{uuid.uuid4().hex[:6]}@example.com"
    client.post("/api/v1/signup", json={"email": email2, "password": "OtherPass123"})
    tok2 = client.post(
        "/api/v1/login",
        json={"email": email2, "password": "OtherPass123"},
    ).json()["access_token"]
    headers2 = {"Authorization": f"Bearer {tok2}"}

    r = client.post(
        "/api/v1/chatbots",
        json={"name": "Mine", "website_url": "https://example.com"},
        headers=auth_headers,
    )
    bot_id = r.json()["id"]

    r2 = client.get(f"/api/v1/chatbots/{bot_id}", headers=headers2)
    assert r2.status_code == 404


def test_widget_origin_blocked(client, auth_headers):
    """Chat request from a blocked origin returns 403."""
    r = client.post(
        "/api/v1/chatbots",
        json={"name": "Gated", "website_url": "https://example.com"},
        headers=auth_headers,
    )
    bot_id = r.json()["id"]
    client.patch(
        f"/api/v1/chatbots/{bot_id}",
        json={"allowed_origins": "https://trusted.com"},
        headers=auth_headers,
    )
    r2 = client.post(
        f"/api/v1/chatbots/{bot_id}/chat",
        json={"session_id": "s1", "message": "hi"},
        headers={"Origin": "https://evil.com"},
    )
    assert r2.status_code == 403
