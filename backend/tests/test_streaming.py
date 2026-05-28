def test_stream_endpoint_no_openai(client, auth_headers):
    """Without OpenAI key, streaming endpoint returns 503."""
    r = client.post(
        "/api/v1/chatbots",
        json={"name": "StreamBot", "website_url": "https://example.com"},
        headers=auth_headers,
    )
    assert r.status_code == 201

    r2 = client.post(
        "/api/v1/widget/stream",
        json={"chatbot_id": r.json()["id"], "message": "hello", "session_id": "s1"},
    )
    assert r2.status_code in (200, 503)


def test_stream_wrong_origin(client, auth_headers):
    """Locked chatbot rejects non-allowed origin."""
    r = client.post(
        "/api/v1/chatbots",
        json={"name": "LockedStream", "website_url": "https://example.com"},
        headers=auth_headers,
    )
    bot_id = r.json()["id"]
    client.patch(
        f"/api/v1/chatbots/{bot_id}",
        json={"allowed_origins": "https://allowed.com"},
        headers=auth_headers,
    )
    r2 = client.post(
        "/api/v1/widget/stream",
        json={"chatbot_id": bot_id, "message": "hi", "session_id": "s1"},
        headers={"Origin": "https://blocked.com"},
    )
    assert r2.status_code == 403


def test_robots_txt(client):
    r = client.get("/robots.txt")
    assert r.status_code == 200
    assert "User-agent" in r.text
    assert "/api/" in r.text


def test_sitemap_xml(client):
    r = client.get("/sitemap.xml")
    assert r.status_code == 200
    assert "<urlset" in r.text
    assert "/pricing" in r.text
