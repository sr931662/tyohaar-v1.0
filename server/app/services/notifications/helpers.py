from __future__ import annotations

import re


def render_template(template_body: str, context: dict) -> str:
    """Simple {variable} substitution."""
    def replace(match: re.Match) -> str:
        key = match.group(1).strip()
        return str(context.get(key, match.group(0)))

    return re.sub(r"\{(\w+)\}", replace, template_body)


def render_subject(template_subject: str, context: dict) -> str:
    return render_template(template_subject, context)


def truncate_notification_body(body: str, max_length: int = 200) -> str:
    if len(body) <= max_length:
        return body
    return body[: max_length - 1] + "…"


def build_notification_payload(template: dict, context: dict) -> dict:
    """Render a template dict into {title, body, data}."""
    title = render_subject(template.get("title_template", ""), context)
    body = render_template(template.get("body_template", ""), context)
    return {
        "title": title,
        "body": body,
        "data": context,
    }
