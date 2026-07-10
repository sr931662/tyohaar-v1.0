"""
FCM Client — thin wrapper around the Firebase Admin SDK for push dispatch.

Credentials come from FIREBASE_CREDENTIALS_JSON (raw service-account JSON,
see app/core/config.py). Until that's set, `is_configured()` returns False
and callers should leave the notification PENDING rather than attempt a send.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)

_firebase_app = None
_init_attempted = False


def _get_app():
    global _firebase_app, _init_attempted
    if _firebase_app is not None:
        return _firebase_app
    if _init_attempted:
        return None
    _init_attempted = True

    if not settings.FIREBASE_CREDENTIALS_JSON:
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials

        cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
        cred = credentials.Certificate(cred_dict)
        _firebase_app = firebase_admin.initialize_app(cred)
        return _firebase_app
    except Exception:
        logger.exception("Failed to initialize Firebase Admin SDK")
        return None


def is_configured() -> bool:
    return _get_app() is not None


@dataclass
class PushResult:
    success_count: int
    failure_count: int
    invalid_tokens: list[str]
    token_success: dict[str, bool]


def send_push(
    tokens: list[str],
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> PushResult:
    """
    Send a push notification to one or more FCM registration tokens.
    Returns a PushResult; callers should deactivate/clear invalid_tokens.
    Raises RuntimeError if Firebase isn't configured — callers must check
    is_configured() first (or catch this) and fall back to PENDING status.
    """
    app = _get_app()
    if app is None:
        raise RuntimeError(
            "Firebase is not configured yet. Set FIREBASE_CREDENTIALS_JSON."
        )

    from firebase_admin import messaging

    if not tokens:
        return PushResult(success_count=0, failure_count=0, invalid_tokens=[], token_success={})

    invalid_tokens: list[str] = []
    token_success: dict[str, bool] = {}
    total_success = 0
    total_failure = 0

    # FCM multicast caps at 500 tokens per call.
    for i in range(0, len(tokens), 500):
        chunk = tokens[i : i + 500]
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            tokens=chunk,
        )
        response = messaging.send_each_for_multicast(message, app=app)
        total_success += response.success_count
        total_failure += response.failure_count

        for token, result in zip(chunk, response.responses):
            token_success[token] = result.success
            if not result.success:
                error_code = getattr(result.exception, "code", None)
                if error_code in ("UNREGISTERED", "INVALID_ARGUMENT", "NOT_FOUND"):
                    invalid_tokens.append(token)
                logger.warning("FCM send failed for token %s: %s", token[:16], result.exception)

    return PushResult(
        success_count=total_success,
        failure_count=total_failure,
        invalid_tokens=invalid_tokens,
        token_success=token_success,
    )
