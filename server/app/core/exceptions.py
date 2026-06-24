from __future__ import annotations

import logging
import traceback
from typing import Any

from fastapi import FastAPI, Request, status

logger = logging.getLogger(__name__)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.repositories.base import (
    AlreadyExistsError,
    DatabaseError,
    NotFoundError as RepoNotFoundError,
    StaleDataError,
)
from app.services.exceptions import (
    AccountLockedError,
    AuthenticationError,
    BookingConflictError,
    BusinessRuleError,
    ConflictError,
    CouponError,
    ExternalServiceError,
    InsufficientBalanceError,
    NotFoundError,
    PaymentError,
    PermissionError as ServicePermissionError,
    RateLimitError,
    ServiceError,
    ValidationError as ServiceValidationError,
)


def _err(code: str, message: str, detail: Any = None) -> dict:
    body: dict = {"error": {"code": code, "message": message}}
    if detail is not None:
        body["error"]["detail"] = detail
    return body


def register_exception_handlers(app: FastAPI) -> None:
    """
    Attach all domain and infrastructure exception handlers to the FastAPI app.

    Call this once during application startup (e.g. in lifespan or main.py).
    Handlers are ordered from most-specific to least-specific within each
    exception family so the correct HTTP status is always returned.
    """

    # ── Pydantic / FastAPI request validation — 422 ───────────────────────────
    @app.exception_handler(RequestValidationError)
    async def _request_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_err("VALIDATION_ERROR", "Request validation failed.", exc.errors()),
        )

    # ── Service: NotFoundError — 404 ──────────────────────────────────────────
    @app.exception_handler(NotFoundError)
    async def _not_found(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=_err("NOT_FOUND", exc.message, exc.detail or None),
        )

    # ── Repository: NotFoundError — 404 ───────────────────────────────────────
    @app.exception_handler(RepoNotFoundError)
    async def _repo_not_found(request: Request, exc: RepoNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=_err("NOT_FOUND", str(exc)),
        )

    # ── BookingConflictError — 409 (must come before ConflictError) ───────────
    @app.exception_handler(BookingConflictError)
    async def _booking_conflict(
        request: Request, exc: BookingConflictError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_err("BOOKING_CONFLICT", exc.message),
        )

    # ── ConflictError — 409 ───────────────────────────────────────────────────
    @app.exception_handler(ConflictError)
    async def _conflict(request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_err("CONFLICT", exc.message, exc.detail or None),
        )

    # ── Repository: AlreadyExistsError — 409 ─────────────────────────────────
    @app.exception_handler(AlreadyExistsError)
    async def _already_exists(
        request: Request, exc: AlreadyExistsError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_err("ALREADY_EXISTS", str(exc)),
        )

    # ── CouponError — 422 (before ServiceValidationError) ────────────────────
    @app.exception_handler(CouponError)
    async def _coupon_error(request: Request, exc: CouponError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_err("COUPON_ERROR", exc.message),
        )

    # ── InsufficientBalanceError — 422 ────────────────────────────────────────
    @app.exception_handler(InsufficientBalanceError)
    async def _insufficient_balance(
        request: Request, exc: InsufficientBalanceError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_err("INSUFFICIENT_BALANCE", exc.message),
        )

    # ── BusinessRuleError — 422 ───────────────────────────────────────────────
    @app.exception_handler(BusinessRuleError)
    async def _business_rule(
        request: Request, exc: BusinessRuleError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_err("BUSINESS_RULE_VIOLATION", exc.message),
        )

    # ── ServiceValidationError — 422 ──────────────────────────────────────────
    @app.exception_handler(ServiceValidationError)
    async def _service_validation(
        request: Request, exc: ServiceValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_err("VALIDATION_ERROR", exc.message, exc.detail or None),
        )

    # ── AccountLockedError — 401 (before AuthenticationError) ────────────────
    @app.exception_handler(AccountLockedError)
    async def _account_locked(
        request: Request, exc: AccountLockedError
    ) -> JSONResponse:
        body = _err("ACCOUNT_LOCKED", exc.message)
        if exc.locked_until:
            body["error"]["locked_until"] = exc.locked_until
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=body,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ── AuthenticationError — 401 ─────────────────────────────────────────────
    @app.exception_handler(AuthenticationError)
    async def _authentication(
        request: Request, exc: AuthenticationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=_err("AUTHENTICATION_FAILED", exc.message),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ── ServicePermissionError — 403 ──────────────────────────────────────────
    @app.exception_handler(ServicePermissionError)
    async def _permission(
        request: Request, exc: ServicePermissionError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=_err("PERMISSION_DENIED", exc.message),
        )

    # ── RateLimitError — 429 ──────────────────────────────────────────────────
    @app.exception_handler(RateLimitError)
    async def _rate_limit(request: Request, exc: RateLimitError) -> JSONResponse:
        headers: dict[str, str] = {}
        if exc.retry_after_seconds is not None:
            headers["Retry-After"] = str(exc.retry_after_seconds)
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=_err("RATE_LIMIT_EXCEEDED", exc.message),
            headers=headers,
        )

    # ── PaymentError — 402 ────────────────────────────────────────────────────
    @app.exception_handler(PaymentError)
    async def _payment(request: Request, exc: PaymentError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content=_err("PAYMENT_ERROR", exc.message),
        )

    # ── Repository: StaleDataError — 409 (optimistic locking) ────────────────
    @app.exception_handler(StaleDataError)
    async def _stale_data(request: Request, exc: StaleDataError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_err(
                "STALE_DATA",
                "The resource was modified by a concurrent request. Retry with fresh data.",
            ),
        )

    # ── ExternalServiceError — 502 ────────────────────────────────────────────
    @app.exception_handler(ExternalServiceError)
    async def _external_service(
        request: Request, exc: ExternalServiceError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=_err("EXTERNAL_SERVICE_ERROR", exc.message),
        )

    # ── Repository: DatabaseError — 503 ───────────────────────────────────────
    @app.exception_handler(DatabaseError)
    async def _database_error(
        request: Request, exc: DatabaseError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=_err("DATABASE_ERROR", "A database error occurred. Please try again."),
        )

    # ── ServiceError (catch-all) — 500 ────────────────────────────────────────
    @app.exception_handler(ServiceError)
    async def _service_error(request: Request, exc: ServiceError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_err("INTERNAL_ERROR", exc.message),
        )

    # ── Generic Exception — 500 (debug: exposes actual error) ─────────────────
    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        tb = traceback.format_exc()
        logger.error("Unhandled exception on %s %s:\n%s", request.method, request.url.path, tb)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_err("INTERNAL_ERROR", f"{type(exc).__name__}: {exc}"),
        )
