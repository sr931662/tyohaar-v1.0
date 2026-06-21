from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.constants import REQUEST_ID_HEADER


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Assigns a unique UUID to every request.

    Resolution order:
        1. Use the value of X-Request-ID if the client provides one.
        2. Generate a fresh UUID4 otherwise.

    Effect:
        - Stores the ID on ``request.state.request_id``.
        - Echoes it back in the X-Request-ID response header.

    Intentionally never logs — the LoggingMiddleware reads the value set here.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id

        response: Response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
