"""
Integration boundary for automated WhatsApp reminders.

Only the official WhatsApp Business Platform (Cloud API) may be used, and only
with an approved template and a recipient who has opted in. None of that is set
up yet, so this module deliberately sends nothing. While ``is_configured()`` is
False the app offers manual reminders: the host taps send, and the message
leaves from their own WhatsApp.

To go live: set WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_ACCESS_TOKEN and
WHATSAPP_REMINDER_TEMPLATE, implement ``send_template`` against
``POST /{phone_number_id}/messages``, record guest opt-in, and add a scheduled
job alongside jobs/purge_job.py that walks ``EventService.reminder_candidates``.
"""

from __future__ import annotations

from app.core.config import settings


def is_configured() -> bool:
    return bool(
        settings.WHATSAPP_PHONE_NUMBER_ID
        and settings.WHATSAPP_ACCESS_TOKEN
        and settings.WHATSAPP_REMINDER_TEMPLATE
    )


async def send_template(*, to_phone: str, parameters: list[str]) -> None:
    raise NotImplementedError(
        "Automated WhatsApp reminders aren't enabled. See this module's docstring."
    )
