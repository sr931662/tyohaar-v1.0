"""
SMS Client — sends one-time codes by text message.

Two providers, picked with SMS_PROVIDER:

  * "msg91"  — MSG91 Flow API (India). Indian operators only deliver
               transactional SMS sent from a DLT-registered template, so the
               template is created and approved in the MSG91 dashboard first;
               SMS_TEMPLATE_ID is its id and SMS_TEMPLATE_OTP_VAR is the name
               of the variable the code is put in (MSG91 default "otp").
  * "twilio" — Twilio Messages API (international). Plain text body.

Until SMS_PROVIDER and its credentials are set, `is_configured()` is False:
phone sign-in is then reported as unavailable in production (see
AuthService.get_provider_config) and only works in development, where the code
is written to the server log instead.

Credentials are never logged; neither is the code itself.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(10.0)


def is_configured() -> bool:
    provider = (settings.SMS_PROVIDER or "").strip().lower()
    if provider == "msg91":
        return bool(settings.SMS_API_KEY and settings.SMS_TEMPLATE_ID)
    if provider == "twilio":
        return bool(settings.SMS_ACCOUNT_SID and settings.SMS_API_KEY and settings.SMS_SENDER)
    return False


def _digits(phone: str) -> str:
    """'+91 98765-43210' -> '919876543210' (MSG91 wants country code, no '+')."""
    return "".join(ch for ch in phone if ch.isdigit())


async def send_otp_sms(phone: str, code: str, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
    """
    Send `code` to `phone` (E.164). Raises RuntimeError if SMS isn't configured
    or the provider rejects the request. `transport` is for tests.
    """
    if not is_configured():
        raise RuntimeError("SMS is not configured. Set SMS_PROVIDER and its credentials.")

    provider = settings.SMS_PROVIDER.strip().lower()
    async with httpx.AsyncClient(timeout=_TIMEOUT, transport=transport) as client:
        if provider == "msg91":
            response = await client.post(
                "https://control.msg91.com/api/v5/flow",
                headers={"authkey": settings.SMS_API_KEY, "accept": "application/json"},
                json={
                    "template_id": settings.SMS_TEMPLATE_ID,
                    "short_url": "0",
                    "recipients": [{"mobiles": _digits(phone), settings.SMS_TEMPLATE_OTP_VAR: code}],
                },
            )
        else:  # twilio
            response = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{settings.SMS_ACCOUNT_SID}/Messages.json",
                auth=(settings.SMS_ACCOUNT_SID, settings.SMS_API_KEY),
                data={
                    "To": phone,
                    "From": settings.SMS_SENDER,
                    "Body": f"{code} is your Tyohaar verification code. It expires in 5 minutes. "
                            f"Don't share it with anyone.",
                },
            )

    if response.status_code >= 400:
        # The body can echo the request (including the code), so log only the status.
        logger.error("SMS provider %s rejected the request: HTTP %s", provider, response.status_code)
        raise RuntimeError(f"SMS provider returned HTTP {response.status_code}")
