"""
Shared condition-tree evaluator.

Used by both the CMS automation engine (AutomationRule.conditions) and the
discount engine (Coupon.condition_rules) — same JSON shape, same evaluation
semantics, extracted once here so neither has its own copy.
"""

from __future__ import annotations

from typing import Any


def evaluate_conditions(
    conditions: dict[str, Any] | None, payload: dict[str, Any]
) -> bool:
    """
    Evaluate a condition tree against a flat payload dict.

    Tree shape: {"op": "AND"|"OR", "clauses": [...]}, where each leaf clause
    is {"field", "operator", "value"} and nested clauses recurse (a clause
    containing its own "op" key is itself a subtree). Supported operators:
    eq, neq, gte, lte, gt, lt, in, contains. An empty/None tree always
    evaluates True (no restriction).
    """
    if not conditions:
        return True

    op = conditions.get("op", "AND")
    clauses = conditions.get("clauses", [])

    results = []
    for clause in clauses:
        if "op" in clause:
            results.append(evaluate_conditions(clause, payload))
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
