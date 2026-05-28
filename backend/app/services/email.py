from __future__ import annotations

import logging

import resend

from app.core.config import settings

logger = logging.getLogger(__name__)


def _send(to: str, subject: str, html: str) -> bool:
    """Send an email via Resend. Returns True on success, False on failure."""
    if not settings.email_enabled:
        logger.info("Email disabled — would send to %s: %s", to, subject)
        return True
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not set — skipping email to %s", to)
        return False
    resend.api_key = settings.resend_api_key
    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to],
            "subject": subject,
            "html": html,
        })
        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to)
        return False


def send_welcome(to: str, name: str = "") -> None:
    greeting = f"Hi {name}," if name else "Hi,"
    _send(
        to=to,
        subject="Welcome to Klyro — your AI chatbot is ready",
        html=f"""
        <div style="font-family:sans-serif;max-width:560px;margin:auto;padding:32px;color:#1e293b">
          <h2 style="margin:0 0 16px;font-size:22px">{greeting}</h2>
          <p>Thanks for signing up for <strong>Klyro</strong>. You can now create your first
          AI chatbot, train it on your website, and embed it in minutes.</p>
          <p style="margin:24px 0">
            <a href="{settings.app_base_url}/dashboard"
               style="background:#6366f1;color:#fff;padding:12px 24px;border-radius:8px;
                      text-decoration:none;font-weight:600">
              Go to dashboard →
            </a>
          </p>
          <p style="color:#64748b;font-size:13px">
            Questions? Reply to this email — we read every one.
          </p>
        </div>
        """,
    )


def send_password_reset(to: str, reset_url: str) -> None:
    _send(
        to=to,
        subject="Reset your Klyro password",
        html=f"""
        <div style="font-family:sans-serif;max-width:560px;margin:auto;padding:32px;color:#1e293b">
          <h2 style="margin:0 0 16px">Reset your password</h2>
          <p>Someone requested a password reset for your Klyro account.
          If this wasn't you, ignore this email.</p>
          <p style="margin:24px 0">
            <a href="{reset_url}"
               style="background:#6366f1;color:#fff;padding:12px 24px;border-radius:8px;
                      text-decoration:none;font-weight:600">
              Reset password →
            </a>
          </p>
          <p style="color:#64748b;font-size:13px">
            This link expires in 30 minutes.
          </p>
        </div>
        """,
    )


def send_lead_notification(
    owner_email: str,
    chatbot_name: str,
    lead_email: str,
    lead_name: str = "",
) -> None:
    _send(
        to=owner_email,
        subject=f"New lead from {chatbot_name}",
        html=f"""
        <div style="font-family:sans-serif;max-width:560px;margin:auto;padding:32px;color:#1e293b">
          <h2 style="margin:0 0 16px">New lead captured 🎉</h2>
          <p>Your chatbot <strong>{chatbot_name}</strong> captured a new lead:</p>
          <table style="border-collapse:collapse;margin:16px 0">
            <tr><td style="padding:6px 12px;color:#64748b">Name</td>
                <td style="padding:6px 12px">{lead_name or '—'}</td></tr>
            <tr><td style="padding:6px 12px;color:#64748b">Email</td>
                <td style="padding:6px 12px">{lead_email}</td></tr>
          </table>
          <p style="margin:24px 0">
            <a href="{settings.app_base_url}/dashboard"
               style="background:#6366f1;color:#fff;padding:12px 24px;border-radius:8px;
                      text-decoration:none;font-weight:600">
              View in dashboard →
            </a>
          </p>
        </div>
        """,
    )
