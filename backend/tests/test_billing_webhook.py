import hashlib
import hmac
import json
import time


def _stripe_sig(payload: bytes, secret: str) -> str:
    ts = str(int(time.time()))
    signed = f"{ts}.{payload.decode()}"
    sig = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def test_webhook_invalid_signature(client):
    r = client.post(
        "/api/v1/billing/webhook",
        content=b'{"type":"test"}',
        headers={"stripe-signature": "t=0,v1=bad"},
    )
    assert r.status_code in (400, 503)
