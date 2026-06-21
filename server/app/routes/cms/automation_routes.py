"""Automation Engine endpoints — /admin/cms/automation/"""

from __future__ import annotations

from fastapi import APIRouter

from app.controllers.cms.automation_controller import (
    create_rule,
    delete_rule,
    get_log,
    get_rule,
    list_logs,
    list_rules,
    manual_trigger,
    toggle_rule,
    update_rule,
)

router = APIRouter(prefix="/automation", tags=["CMS — Automation Engine"])

# ── Rules ─────────────────────────────────────────────────────────────────────

router.add_api_route(
    "/rules",
    list_rules,
    methods=["GET"],
    summary="List automation rules with optional filters",
)
router.add_api_route(
    "/rules",
    create_rule,
    methods=["POST"],
    summary="Create a new automation rule",
)
router.add_api_route(
    "/rules/{rule_id}",
    get_rule,
    methods=["GET"],
    summary="Get single automation rule",
)
router.add_api_route(
    "/rules/{rule_id}",
    update_rule,
    methods=["PATCH"],
    summary="Update automation rule",
)
router.add_api_route(
    "/rules/{rule_id}",
    delete_rule,
    methods=["DELETE"],
    summary="Delete automation rule",
)
router.add_api_route(
    "/rules/{rule_id}/toggle",
    toggle_rule,
    methods=["POST"],
    summary="Enable / disable an automation rule",
)
router.add_api_route(
    "/rules/{rule_id}/trigger",
    manual_trigger,
    methods=["POST"],
    summary="Manually trigger an automation rule with a custom payload",
)

# ── Logs ──────────────────────────────────────────────────────────────────────

router.add_api_route(
    "/logs",
    list_logs,
    methods=["GET"],
    summary="List automation execution logs",
)
router.add_api_route(
    "/logs/{log_id}",
    get_log,
    methods=["GET"],
    summary="Get single automation log entry",
)
