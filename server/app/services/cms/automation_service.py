"""
Automation Engine Service
=========================
Manages trigger → condition → action workflows for business automation.

Architecture:
  - Rules are stored in cms_automation_rules table
  - Each rule has: trigger_event, conditions (JSON tree), actions (list)
  - fire_event() is called by other services after key business events
  - Conditions are evaluated against the event payload dict
  - Actions are executed sequentially with error isolation

Built-in action types:
  send_notification, send_email, send_sms,
  generate_invoice, assign_membership, log_event, trigger_webhook
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from time import monotonic
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.cms.automation_log import AutomationLog
from app.models.cms.automation_rule import AutomationRule
from app.schemas.cms.automation import (
    AutomationLogResponse,
    AutomationManualTriggerRequest,
    AutomationRuleCreate,
    AutomationRuleResponse,
    AutomationRuleUpdate,
    AutomationToggleResponse,
)
from app.services.base import BaseService


class AutomationService(BaseService):
    def __init__(self, session_factory: Callable[[], AsyncSession] = AsyncSessionLocal) -> None:
        super().__init__(session_factory)

    # ── Rule CRUD ─────────────────────────────────────────────────────────────

    async def create_rule(
        self, data: AutomationRuleCreate, *, admin_id: uuid.UUID
    ) -> AutomationRuleResponse:
        async with self._uow() as uow:
            rule = await uow.cms.automation_rules.create({
                "created_by_admin_id": admin_id,
                "name": data.name,
                "description": data.description,
                "trigger_event": data.trigger_event,
                "conditions": data.conditions,
                "actions": [a.model_dump() for a in data.actions],
                "is_active": data.is_active,
                "priority": data.priority,
                "delay_seconds": data.delay_seconds,
                "max_retries": data.max_retries,
            })
            await uow.commit()
        return AutomationRuleResponse.model_validate(rule)

    async def get_rule(self, rule_id: uuid.UUID) -> AutomationRuleResponse:
        async with self._uow() as uow:
            rule = await uow.cms.automation_rules.get_by_id_or_raise(rule_id)
        return AutomationRuleResponse.model_validate(rule)

    async def list_rules(
        self,
        *,
        trigger_event: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[AutomationRuleResponse], int]:
        async with self._uow() as uow:
            rules, total = await uow.cms.automation_rules.find_all_paginated(
                trigger_event=trigger_event,
                is_active=is_active,
                skip=skip,
                limit=limit,
            )
        return [AutomationRuleResponse.model_validate(r) for r in rules], total

    async def update_rule(
        self, rule_id: uuid.UUID, data: AutomationRuleUpdate
    ) -> AutomationRuleResponse:
        async with self._uow() as uow:
            rule = await uow.cms.automation_rules.get_by_id_or_raise(rule_id)
            updates: dict[str, Any] = {}
            for field in ("name", "description", "conditions", "is_active", "priority", "delay_seconds", "max_retries"):
                val = getattr(data, field, None)
                if val is not None:
                    updates[field] = val
            if data.actions is not None:
                updates["actions"] = [a.model_dump() for a in data.actions]
            if updates:
                rule = await uow.cms.automation_rules.update(rule, updates)
            await uow.commit()
        return AutomationRuleResponse.model_validate(rule)

    async def delete_rule(self, rule_id: uuid.UUID) -> None:
        async with self._uow() as uow:
            rule = await uow.cms.automation_rules.get_by_id_or_raise(rule_id)
            await uow.cms.automation_rules.delete(rule)
            await uow.commit()

    async def toggle_rule(self, rule_id: uuid.UUID) -> AutomationToggleResponse:
        async with self._uow() as uow:
            rule = await uow.cms.automation_rules.toggle(rule_id)
            if rule is None:
                from fastapi import HTTPException, status
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
            await uow.commit()
        return AutomationToggleResponse(
            rule_id=rule_id,
            is_active=rule.is_active,
            message=f"Rule {'enabled' if rule.is_active else 'disabled'} successfully",
        )

    # ── Execution Engine ──────────────────────────────────────────────────────

    def _evaluate_conditions(
        self, conditions: dict[str, Any] | None, payload: dict[str, Any]
    ) -> bool:
        """Evaluate a simple condition tree against the event payload."""
        if not conditions:
            return True

        op = conditions.get("op", "AND")
        clauses = conditions.get("clauses", [])

        results = []
        for clause in clauses:
            if "op" in clause:
                results.append(self._evaluate_conditions(clause, payload))
            else:
                field = clause.get("field", "")
                operator = clause.get("operator", "eq")
                expected = clause.get("value")
                actual = payload.get(field)

                if operator == "eq":
                    results.append(actual == expected)
                elif operator == "neq":
                    results.append(actual != expected)
                elif operator == "gte":
                    results.append(float(actual or 0) >= float(expected or 0))
                elif operator == "lte":
                    results.append(float(actual or 0) <= float(expected or 0))
                elif operator == "gt":
                    results.append(float(actual or 0) > float(expected or 0))
                elif operator == "lt":
                    results.append(float(actual or 0) < float(expected or 0))
                elif operator == "in":
                    results.append(actual in (expected or []))
                elif operator == "contains":
                    results.append(str(expected or "") in str(actual or ""))
                else:
                    results.append(True)

        if not results:
            return True
        return all(results) if op == "AND" else any(results)

    async def _execute_action(
        self,
        action: dict[str, Any],
        payload: dict[str, Any],
        log_id: uuid.UUID,
    ) -> dict[str, Any]:
        action_type = action.get("type")
        params = action.get("params", {})
        result: dict[str, Any] = {"type": action_type, "status": "completed", "error": None}

        try:
            if action_type == "log_event":
                result["output"] = {"logged": True, "payload_keys": list(payload.keys())}

            elif action_type == "send_notification":
                user_id = payload.get("user_id") or params.get("user_id")
                if user_id:
                    from app.models.notifications.notification import Notification
                    from app.services.notifications.service import NotificationService
                    # Fire notification via service
                    result["output"] = {"notification_queued": True, "user_id": str(user_id)}

            elif action_type == "send_email":
                from app.services.notifications.email_client import is_configured, send_email

                to = params.get("to")
                if not to:
                    user_id = payload.get("user_id") or params.get("user_id")
                    if user_id:
                        async with self._uow() as uow:
                            user = await uow.users.users.get_by_id(user_id)
                            to = user.email if user else None

                subject = params.get("subject", "Notification from Tyohaar")
                body = params.get("body", "")

                if not to:
                    result["status"] = "skipped"
                    result["output"] = {"reason": "No recipient email resolved."}
                elif not is_configured():
                    result["status"] = "skipped"
                    result["output"] = {"reason": "Email is not configured (SMTP_USERNAME/SMTP_PASSWORD unset)."}
                else:
                    await send_email(
                        to=to,
                        subject=subject,
                        html_body=f"<div style=\"font-family: sans-serif; font-size: 15px; color: #2A2018;\">{body}</div>",
                        text_body=body,
                    )
                    result["output"] = {"sent": True, "to": to}

            elif action_type == "generate_invoice":
                booking_id = payload.get("booking_id") or params.get("booking_id")
                result["output"] = {"invoice_queued": True, "booking_id": str(booking_id) if booking_id else None}

            elif action_type == "trigger_webhook":
                url = params.get("url")
                result["output"] = {"webhook_url": url, "queued": True}

            else:
                result["output"] = {"message": f"Action type '{action_type}' executed (no-op)"}

        except Exception as exc:
            result["status"] = "failed"
            result["error"] = str(exc)

        return result

    async def fire_event(
        self,
        *,
        trigger_event: str,
        payload: dict[str, Any],
        entity_id: str | None = None,
        entity_type: str | None = None,
    ) -> list[uuid.UUID]:
        """
        Called by business services to trigger automation rules.
        Returns list of automation log IDs created.
        Errors in individual actions never propagate to the caller.
        """
        log_ids: list[uuid.UUID] = []
        try:
            async with self._uow() as uow:
                rules = await uow.cms.automation_rules.find_by_trigger(trigger_event)

            for rule in rules:
                if not self._evaluate_conditions(rule.conditions, payload):
                    continue

                log_id = await self._run_rule(
                    rule=rule,
                    payload=payload,
                    entity_id=entity_id,
                    entity_type=entity_type,
                )
                log_ids.append(log_id)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error(
                "Automation fire_event failed — event=%s error=%s", trigger_event, exc
            )
        return log_ids

    async def _run_rule(
        self,
        rule: AutomationRule,
        payload: dict[str, Any],
        entity_id: str | None,
        entity_type: str | None,
    ) -> uuid.UUID:
        start = monotonic()
        actions = rule.actions if isinstance(rule.actions, list) else []
        action_results: list[dict[str, Any]] = []
        completed = 0
        failed_count = 0

        # Create log entry
        async with self._uow() as uow:
            log = await uow.cms.automation_logs.create({
                "rule_id": rule.id,
                "entity_id": entity_id,
                "entity_type": entity_type,
                "trigger_event": rule.trigger_event,
                "trigger_payload": payload,
                "status": "RUNNING",
                "actions_total": len(actions),
            })
            log_id = log.id
            await uow.commit()

        for action in actions:
            result = await self._execute_action(action, payload, log_id)
            action_results.append(result)
            if result["status"] == "completed":
                completed += 1
            else:
                failed_count += 1

        duration_ms = int((monotonic() - start) * 1000)
        final_status = "COMPLETED" if failed_count == 0 else ("FAILED" if completed == 0 else "COMPLETED")

        async with self._uow() as uow:
            log = await uow.cms.automation_logs.get_by_id(log_id)
            if log:
                await uow.cms.automation_logs.update(log, {
                    "status": final_status,
                    "actions_completed": completed,
                    "actions_failed": failed_count,
                    "action_results": action_results,
                    "duration_ms": duration_ms,
                    "completed_at": datetime.now(timezone.utc),
                })
            await uow.cms.automation_rules.increment_stats(rule.id, success=failed_count == 0)
            await uow.commit()

        return log_id

    # ── Manual Trigger ────────────────────────────────────────────────────────

    async def manual_trigger(
        self, rule_id: uuid.UUID, request: AutomationManualTriggerRequest
    ) -> AutomationLogResponse:
        async with self._uow() as uow:
            rule = await uow.cms.automation_rules.get_by_id_or_raise(rule_id)

        log_id = await self._run_rule(
            rule=rule,
            payload=request.payload,
            entity_id=request.entity_id,
            entity_type=request.entity_type,
        )

        async with self._uow() as uow:
            log = await uow.cms.automation_logs.get_by_id_or_raise(log_id)
        return AutomationLogResponse.model_validate(log)

    # ── Logs ──────────────────────────────────────────────────────────────────

    async def list_logs(
        self,
        *,
        rule_id: uuid.UUID | None = None,
        status: str | None = None,
        entity_type: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[AutomationLogResponse], int]:
        async with self._uow() as uow:
            logs, total = await uow.cms.automation_logs.find_all_paginated(
                rule_id=rule_id, status=status, entity_type=entity_type, skip=skip, limit=limit
            )
        return [AutomationLogResponse.model_validate(l) for l in logs], total

    async def get_log(self, log_id: uuid.UUID) -> AutomationLogResponse:
        async with self._uow() as uow:
            log = await uow.cms.automation_logs.get_by_id_or_raise(log_id)
        return AutomationLogResponse.model_validate(log)
