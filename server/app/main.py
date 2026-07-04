"""
Tyohaar API — Application Factory
===================================

Entry point consumed by uvicorn:

    uvicorn app.main:app --host 0.0.0.0 --port 8000

The ``create_app`` factory is also importable for testing:

    from app.main import create_app
    app = create_app()
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import check_database_health, ping_database
from app.core.exceptions import register_exception_handlers
from app.core.lifespan import lifespan
from app.middleware import (
    LoggingMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
from app.routes import all_routers

# ── OpenAPI tag definitions ───────────────────────────────────────────────────

_OPENAPI_TAGS: list[dict] = [
    {
        "name": "Auth",
        "description": (
            "OTP-based authentication, JWT token rotation, "
            "and multi-device session management."
        ),
    },
    {
        "name": "Users",
        "description": (
            "User profiles, addresses, and device registration."
        ),
    },
    {
        "name": "Vendors",
        "description": (
            "Vendor profiles, services, gallery, availability, "
            "bank details, and reviews."
        ),
    },
    {
        "name": "Occasions",
        "description": (
            "Occasion categories, celebrations, guest lists, "
            "timelines, checklists, and budgets."
        ),
    },
    {
        "name": "Packages",
        "description": (
            "Package catalog, items, add-ons, pricing tiers, "
            "discounts, reviews, and FAQs."
        ),
    },
    {
        "name": "Bookings",
        "description": (
            "Create, view, cancel, and reschedule event bookings; "
            "status history and assignment management."
        ),
    },
    {
        "name": "Payments",
        "description": (
            "Payment initiation, verification, refunds, settlements, "
            "webhook handling, and invoices."
        ),
    },
    {
        "name": "Wallets",
        "description": (
            "Wallet balance, transaction history, reward points, "
            "peer transfers, and withdrawals."
        ),
    },
    {
        "name": "Memberships",
        "description": (
            "Membership plans, subscriptions, upgrades, "
            "and cancellations."
        ),
    },
    {
        "name": "Notifications",
        "description": (
            "Send push / SMS / email notifications, list, "
            "mark as read, and manage preferences."
        ),
    },
    {
        "name": "Support",
        "description": (
            "Support tickets, threaded messages, attachments, "
            "and escalation workflows."
        ),
    },
    {
        "name": "Media",
        "description": (
            "Secure file upload, image processing, "
            "gallery management, and document storage."
        ),
    },
    {
        "name": "Referrals",
        "description": (
            "Referral link generation, conversion tracking, "
            "and reward claiming."
        ),
    },
    {
        "name": "Budgets",
        "description": (
            "Budget planning, expense categories, expense entries, "
            "health reports, and threshold alerts."
        ),
    },
    {
        "name": "Admin",
        "description": (
            "User management, role/permission administration, "
            "audit logs, and operational reports."
        ),
    },
    {
        "name": "Common",
        "description": (
            "Shared platform resources: states, cities, FAQs, "
            "banners, app settings, terms, and privacy policy."
        ),
    },
    {
        "name": "Health",
        "description": "Liveness, readiness, and health-check probes.",
    },
    {
        "name": "CMS — Analytics",
        "description": (
            "Executive dashboard, revenue/booking/user/vendor metrics, "
            "time-series charts, geographic breakdown, and activity feed."
        ),
    },
    {
        "name": "CMS — CRM",
        "description": (
            "360° vendor and customer CRM profiles: KYC, financials, "
            "ratings, booking history, wallet, referrals, and support."
        ),
    },
    {
        "name": "CMS — Import/Export",
        "description": (
            "Excel/CSV import with validation, dry-run preview, rollback; "
            "export to XLSX/CSV/JSON with scheduling and download links."
        ),
    },
    {
        "name": "CMS — Bulk Operations",
        "description": (
            "Bulk vendor approve/reject/suspend, package publish/archive, "
            "price updates, notification blasts, coupon generation, membership assignment."
        ),
    },
    {
        "name": "CMS — Global Search",
        "description": (
            "One search across users, vendors, packages, bookings, "
            "tickets, categories, and occasions with per-type result groups."
        ),
    },
    {
        "name": "CMS — Automation Engine",
        "description": (
            "Trigger → condition → action automation rules. "
            "CRUD for rules, manual trigger, execution logs, and toggle."
        ),
    },
]


# ── Health endpoint handlers ──────────────────────────────────────────────────

async def _root_handler():
    """Service identity — always returns 200."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT.value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def _health_handler():
    """
    Deep health check.

    Probes the database connection and validates that configuration loaded
    cleanly.  Returns 200 when healthy, 503 when degraded.
    """
    db = await check_database_health()
    is_healthy = db["status"] == "healthy"
    return JSONResponse(
        status_code=status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "healthy" if is_healthy else "unhealthy",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT.value,
            "checks": {
                "database": db,
                "configuration": "valid",
            },
        },
    )


async def _ready_handler():
    """
    Readiness probe — used by orchestrators (k8s, ECS) to gate traffic.

    Returns 200 only when the database is reachable.
    """
    ok = await ping_database()
    return JSONResponse(
        status_code=status.HTTP_200_OK if ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"ready": ok},
    )


async def _live_handler():
    """
    Liveness probe — confirms the process is alive and the event loop runs.

    Always returns 200; never performs I/O.
    """
    return {"alive": True}


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """
    Build and configure the FastAPI application.

    Lifecycle:
        1. Construct FastAPI with metadata, OpenAPI tags, and the lifespan handler.
        2. Register middleware (outermost last per Starlette add_middleware semantics).
        3. Register global exception handlers.
        4. Include all 16 domain routers under /api/v1.
        5. Attach health / probe endpoints.

    Returns:
        A fully configured FastAPI application ready for an ASGI server.
    """

    # ── FastAPI instance ──────────────────────────────────────────────────────
    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "**Tyohaar** is a celebration & event management platform that "
            "connects customers with curated vendors for weddings, birthdays, "
            "and cultural occasions across India.\n\n"
            "All API endpoints are versioned under `/api/v1`. "
            "Authentication uses OTP → Bearer JWT."
        ),
        version=settings.APP_VERSION,
        openapi_tags=_OPENAPI_TAGS,
        # Swagger/ReDoc expose the full API surface (including admin endpoint
        # shapes) to anyone — keep them available in dev/staging but off in
        # production. Health/liveness/readiness probes still work either way.
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
        lifespan=lifespan,
        # Suppress the default 422 responses from FastAPI's own schema so our
        # custom error envelope is the canonical shape in docs.
        responses={
            422: {
                "description": "Validation Error",
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": "#/components/schemas/ErrorEnvelope"
                        }
                    }
                },
            }
        },
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    # add_middleware is LIFO: last call = outermost = first to handle the request.
    #
    # Execution order (request → response):
    #   TrustedHostMiddleware → CORSMiddleware → RequestIDMiddleware
    #   → LoggingMiddleware → SecurityHeadersMiddleware → GZipMiddleware → App

    # 1. Innermost: compress eligible response bodies before adding headers.
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    # 2. Append security response headers after body is ready.
    app.add_middleware(SecurityHeadersMiddleware)

    # 3. Structured access log — reads request_id set by the next middleware.
    app.add_middleware(LoggingMiddleware)

    # 4. Assign / propagate X-Request-ID before logging runs.
    app.add_middleware(RequestIDMiddleware)

    # 5. CORS — handle OPTIONS preflight and inject CORS response headers.
    # allow_credentials=True is incompatible with allow_origins=["*"] per the CORS spec.
    # When wildcard is configured we use allow_origin_regex instead so every origin
    # receives its own reflected value rather than the literal "*".
    _origins = settings.ALLOWED_ORIGINS
    _origin_regex = None
    if "*" in _origins:
        _origins = []
        _origin_regex = ".*"
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_origin_regex=_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Correlation-ID", "Retry-After"],
    )

    # 6. Outermost: reject requests with an unrecognised Host header.
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )

    # ── Exception handlers ────────────────────────────────────────────────────
    register_exception_handlers(app)

    # ── Domain routers ────────────────────────────────────────────────────────
    for router in all_routers:
        app.include_router(router, prefix=settings.API_V1_PREFIX)

    # ── Health / probe endpoints ──────────────────────────────────────────────
    app.add_api_route(
        "/",
        _root_handler,
        methods=["GET"],
        include_in_schema=False,
        summary="Service identity",
    )
    app.add_api_route(
        "/health",
        _health_handler,
        methods=["GET"],
        tags=["Health"],
        summary="Deep health check",
        description=(
            "Probes the database and verifies configuration. "
            "Returns 200 when healthy, 503 when degraded."
        ),
        operation_id="health_check",
    )
    app.add_api_route(
        "/ready",
        _ready_handler,
        methods=["GET"],
        tags=["Health"],
        summary="Readiness probe",
        description=(
            "Returns 200 only when the service is ready to accept traffic "
            "(database reachable). Used by orchestrators to gate routing."
        ),
        operation_id="readiness_probe",
    )
    app.add_api_route(
        "/live",
        _live_handler,
        methods=["GET"],
        tags=["Health"],
        summary="Liveness probe",
        description=(
            "Always returns 200. Confirms the process is alive. "
            "Never performs I/O."
        ),
        operation_id="liveness_probe",
    )

    return app


# ── Module-level app instance (consumed by uvicorn) ───────────────────────────
app = create_app()
