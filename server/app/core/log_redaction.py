"""
Keep guest invitation tokens out of our logs.

A personal link carries its token in the URL path (WhatsApp previews need the
server to see it), and that token is what lets someone view and answer that
invitation. Our access log, and uvicorn's, record paths, so they pass through
here first. Infrastructure logs in front of the app (Cloud Run, Cloudflare)
still see the URL; a leaked link is contained by rotating it from the app.
"""

from __future__ import annotations

import logging
import re

_INVITE_PATH = re.compile(r"(/i/)(?!_api\b)[^/\s\"?]+")


def redact_invite_path(text: str) -> str:
    return _INVITE_PATH.sub(r"\1[redacted]", text)


class InviteTokenLogFilter(logging.Filter):
    """Rewrites any invite path in a log record's message and arguments."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str) and "/i/" in record.msg:
            record.msg = redact_invite_path(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(
                redact_invite_path(a) if isinstance(a, str) and "/i/" in a else a
                for a in record.args
            )
        return True


def install() -> None:
    log_filter = InviteTokenLogFilter()
    for name in ("uvicorn.access", "tyohaar.access"):
        logging.getLogger(name).addFilter(log_filter)
