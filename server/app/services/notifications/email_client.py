"""
Email Client — Gmail SMTP relay using an App Password.

Credentials come from SMTP_USERNAME/SMTP_PASSWORD (see app/core/config.py).
Until both are set, `is_configured()` returns False and callers should
leave the OTP/notification PENDING (or raise a clear error) rather than
attempt a send — mirrors the fcm_client.py pattern for push.
"""

from __future__ import annotations

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    return bool(settings.SMTP_USERNAME and settings.SMTP_PASSWORD)


async def send_email(
    to: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> None:
    """
    Send a single email via Gmail's SMTP relay (STARTTLS on port 587).

    Raises RuntimeError if SMTP isn't configured — callers must check
    is_configured() first (or catch this) and fall back to PENDING status,
    same convention as fcm_client.send_push().
    """
    if not is_configured():
        raise RuntimeError(
            "Email is not configured yet. Set SMTP_USERNAME and SMTP_PASSWORD "
            "(a Gmail App Password, not the account's real password)."
        )

    from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"{settings.SMTP_FROM_NAME} <{from_email}>"
    message["To"] = to

    if text_body:
        message.attach(MIMEText(text_body, "plain"))
    message.attach(MIMEText(html_body, "html"))

    # Gmail app passwords are often copy-pasted with spaces (as displayed
    # in the Google Account UI) — strip them so a pasted value still works.
    password = settings.SMTP_PASSWORD.replace(" ", "")

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=password,
            start_tls=True,
        )
    except Exception:
        logger.exception("Failed to send email to %s", to)
        raise
