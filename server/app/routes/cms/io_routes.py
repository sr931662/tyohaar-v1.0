"""Import / Export endpoints — /admin/cms/io/"""

from __future__ import annotations

from fastapi import APIRouter

from app.controllers.cms.io_controller import (
    download_export,
    execute_import,
    get_export_log,
    get_import_log,
    get_import_template,
    list_export_logs,
    list_import_logs,
    trigger_export,
    undo_import,
    validate_import,
)

router = APIRouter(prefix="/io", tags=["CMS — Import/Export"])

# ── Import ────────────────────────────────────────────────────────────────────

router.add_api_route(
    "/import/template",
    get_import_template,
    methods=["GET"],
    summary="Download column-header template XLSX for an entity type",
)
router.add_api_route(
    "/import/validate",
    validate_import,
    methods=["POST"],
    summary="Validate & preview an uploaded file before import",
)
router.add_api_route(
    "/import/execute",
    execute_import,
    methods=["POST"],
    summary="Execute a previously validated import log",
)
router.add_api_route(
    "/import/logs",
    list_import_logs,
    methods=["GET"],
    summary="List import logs with optional filters",
)
router.add_api_route(
    "/import/logs/{log_id}",
    get_import_log,
    methods=["GET"],
    summary="Get single import log details",
)
router.add_api_route(
    "/import/logs/{log_id}/undo",
    undo_import,
    methods=["POST"],
    summary="Rollback / undo a completed import",
)

# ── Export ────────────────────────────────────────────────────────────────────

router.add_api_route(
    "/export",
    trigger_export,
    methods=["POST"],
    summary="Trigger an export job (XLSX / CSV / JSON)",
)
router.add_api_route(
    "/export/logs",
    list_export_logs,
    methods=["GET"],
    summary="List export logs with optional filters",
)
router.add_api_route(
    "/export/logs/{log_id}",
    get_export_log,
    methods=["GET"],
    summary="Get single export log details",
)
router.add_api_route(
    "/export/logs/{log_id}/download",
    download_export,
    methods=["GET"],
    summary="Download the generated export file",
)
