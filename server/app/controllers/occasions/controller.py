"""
Occasions Controller — occasions reference data, celebrations, guests, checklist, timeline, notes.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends

from app.core.current_user import CurrentUserDep
from app.core.dependencies import OccasionServiceDep
from app.core.pagination import CursorPaginationParams, get_cursor_pagination
from app.core.permissions import AdminDep
from app.core.responses import CursorMeta, CursorPaginatedResponse, SuccessResponse
from app.schemas.base import CursorPage
from app.schemas.occasions import (
    CelebrationChecklistCreate,
    CelebrationChecklistResponse,
    CelebrationChecklistUpdate,
    CelebrationCreate,
    CelebrationGuestCreate,
    CelebrationGuestResponse,
    CelebrationGuestUpdate,
    CelebrationResponse,
    CelebrationUpdate,
    GuestRSVPPublicResponse,
    GuestRSVPSubmit,
    OccasionCreate,
    OccasionFilters,
    OccasionMoodResponse,
    OccasionResponse,
    OccasionTagResponse,
    OccasionThemeResponse,
)
from app.services.occasions.service import (
    CelebrationNoteCreate,
    CelebrationNoteResponse,
    CelebrationNoteUpdate,
    CelebrationTimelineCreate,
    CelebrationTimelineResponse,
    CelebrationTimelineUpdate,
    OccasionCategoryCreate,
    OccasionCategoryResponse,
    OccasionMoodCreate,
    OccasionTagCreate,
    OccasionThemeCreate,
    OccasionUpdate,
)


def _cursor_resp(page: CursorPage, page_size: int) -> CursorPaginatedResponse:
    return CursorPaginatedResponse(
        data=page.items,
        meta=CursorMeta(cursor=page.next_cursor, has_next=page.has_more, page_size=page_size),
    )


# ── Occasions (reference data) ─────────────────────────────────────────────────

async def list_occasions(
    filters: Annotated[OccasionFilters, Depends()],
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    service: OccasionServiceDep,
) -> CursorPaginatedResponse[OccasionResponse]:
    page = await service.list_occasions(
        filters=filters, cursor=pagination.cursor, limit=pagination.page_size
    )
    return _cursor_resp(page, pagination.page_size)


async def get_occasion(
    occasion_id: uuid.UUID,
    service: OccasionServiceDep,
) -> SuccessResponse[OccasionResponse]:
    result = await service.get_occasion(occasion_id=occasion_id)
    return SuccessResponse(data=result, message="Occasion retrieved.")


async def list_occasion_categories(
    service: OccasionServiceDep,
) -> SuccessResponse[list[OccasionCategoryResponse]]:
    categories = await service.list_occasion_categories()
    return SuccessResponse(data=categories, message="Categories retrieved.")


async def list_occasion_moods(
    service: OccasionServiceDep,
) -> SuccessResponse[list[OccasionMoodResponse]]:
    moods = await service.list_occasion_moods()
    return SuccessResponse(data=moods, message="Moods retrieved.")


async def list_occasion_tags(
    service: OccasionServiceDep,
) -> SuccessResponse[list[OccasionTagResponse]]:
    tags = await service.list_occasion_tags()
    return SuccessResponse(data=tags, message="Tags retrieved.")


async def list_occasion_themes(
    service: OccasionServiceDep,
) -> SuccessResponse[list[OccasionThemeResponse]]:
    themes = await service.list_occasion_themes()
    return SuccessResponse(data=themes, message="Themes retrieved.")


# ── Admin operations ───────────────────────────────────────────────────────────

async def create_occasion(
    body: OccasionCreate,
    _admin: AdminDep,
    service: OccasionServiceDep,
) -> SuccessResponse[OccasionResponse]:
    result = await service.create_occasion(data=body)
    return SuccessResponse(data=result, message="Occasion created.")


async def update_occasion(
    occasion_id: uuid.UUID,
    body: OccasionUpdate,
    _admin: AdminDep,
    service: OccasionServiceDep,
) -> SuccessResponse[OccasionResponse]:
    result = await service.update_occasion(occasion_id=occasion_id, data=body)
    return SuccessResponse(data=result, message="Occasion updated.")


async def delete_occasion(
    occasion_id: uuid.UUID,
    _admin: AdminDep,
    service: OccasionServiceDep,
) -> SuccessResponse[None]:
    await service.delete_occasion(occasion_id=occasion_id)
    return SuccessResponse(data=None, message="Occasion deleted.")


async def create_category(
    body: OccasionCategoryCreate,
    _admin: AdminDep,
    service: OccasionServiceDep,
) -> SuccessResponse[OccasionCategoryResponse]:
    result = await service.create_category(data=body)
    return SuccessResponse(data=result, message="Category created.")


async def create_mood(
    body: OccasionMoodCreate,
    _admin: AdminDep,
    service: OccasionServiceDep,
) -> SuccessResponse[OccasionMoodResponse]:
    result = await service.create_mood(data=body)
    return SuccessResponse(data=result, message="Mood created.")


async def create_tag(
    body: OccasionTagCreate,
    _admin: AdminDep,
    service: OccasionServiceDep,
) -> SuccessResponse[OccasionTagResponse]:
    result = await service.create_tag(data=body)
    return SuccessResponse(data=result, message="Tag created.")


async def create_theme(
    body: OccasionThemeCreate,
    _admin: AdminDep,
    service: OccasionServiceDep,
) -> SuccessResponse[OccasionThemeResponse]:
    result = await service.create_theme(data=body)
    return SuccessResponse(data=result, message="Theme created.")


# ── Celebrations ───────────────────────────────────────────────────────────────

async def create_celebration(
    body: CelebrationCreate,
    current_user: CurrentUserDep,
    service: OccasionServiceDep,
) -> SuccessResponse[CelebrationResponse]:
    result = await service.create_celebration(user_id=current_user.id, data=body)
    return SuccessResponse(data=result, message="Celebration created.")


async def get_celebration(
    celebration_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: OccasionServiceDep,
) -> SuccessResponse[CelebrationResponse]:
    result = await service.get_celebration(
        celebration_id=celebration_id, user_id=current_user.id
    )
    return SuccessResponse(data=result, message="Celebration retrieved.")


async def list_celebrations(
    current_user: CurrentUserDep,
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    service: OccasionServiceDep,
) -> CursorPaginatedResponse[CelebrationResponse]:
    page = await service.list_celebrations(
        user_id=current_user.id, cursor=pagination.cursor, limit=pagination.page_size
    )
    return _cursor_resp(page, pagination.page_size)


async def update_celebration(
    celebration_id: uuid.UUID,
    body: CelebrationUpdate,
    current_user: CurrentUserDep,
    service: OccasionServiceDep,
) -> SuccessResponse[CelebrationResponse]:
    result = await service.update_celebration(
        celebration_id=celebration_id, user_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Celebration updated.")


async def delete_celebration(
    celebration_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: OccasionServiceDep,
) -> SuccessResponse[None]:
    await service.delete_celebration(
        celebration_id=celebration_id, user_id=current_user.id
    )
    return SuccessResponse(data=None, message="Celebration deleted.")


# ── Guests ─────────────────────────────────────────────────────────────────────

async def add_guest(
    celebration_id: uuid.UUID,
    body: CelebrationGuestCreate,
    current_user: CurrentUserDep,
    service: OccasionServiceDep,
) -> SuccessResponse[CelebrationGuestResponse]:
    result = await service.add_guest(
        celebration_id=celebration_id, user_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Guest added.")


async def update_guest(
    celebration_id: uuid.UUID,
    guest_id: uuid.UUID,
    body: CelebrationGuestUpdate,
    current_user: CurrentUserDep,
    service: OccasionServiceDep,
) -> SuccessResponse[CelebrationGuestResponse]:
    result = await service.update_guest(
        celebration_id=celebration_id,
        guest_id=guest_id,
        user_id=current_user.id,
        data=body,
    )
    return SuccessResponse(data=result, message="Guest updated.")


async def remove_guest(
    celebration_id: uuid.UUID,
    guest_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: OccasionServiceDep,
) -> SuccessResponse[None]:
    await service.remove_guest(
        celebration_id=celebration_id, guest_id=guest_id, user_id=current_user.id
    )
    return SuccessResponse(data=None, message="Guest removed.")


async def list_guests(
    celebration_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: OccasionServiceDep,
) -> SuccessResponse[list[CelebrationGuestResponse]]:
    guests = await service.list_guests(
        celebration_id=celebration_id, user_id=current_user.id
    )
    return SuccessResponse(data=guests, message="Guests retrieved.")


# ── Public RSVP (no auth) ───────────────────────────────────────────────────────

async def get_guest_rsvp(
    token: str,
    service: OccasionServiceDep,
) -> SuccessResponse[GuestRSVPPublicResponse]:
    result = await service.get_guest_rsvp(token=token)
    return SuccessResponse(data=result, message="Invitation retrieved.")


async def submit_guest_rsvp(
    token: str,
    body: GuestRSVPSubmit,
    service: OccasionServiceDep,
) -> SuccessResponse[GuestRSVPPublicResponse]:
    result = await service.submit_guest_rsvp(token=token, data=body)
    return SuccessResponse(data=result, message="RSVP recorded.")


async def get_guest_rsvp_page(token: str):
    """
    A minimal, self-contained mobile web page for guests who don't have the
    app installed — the WhatsApp/email invite link points here. Renders
    server-side (no React build) and talks to the JSON RSVP endpoints above
    via fetch(). Kept deliberately simple: no build step, no dependencies.
    """
    from fastapi.responses import HTMLResponse

    html = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>You're Invited — Tyohaar</title>
<style>
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: #FFF8F0; margin: 0; padding: 24px 16px; color: #1A1A1A; }
  .card { max-width: 420px; margin: 0 auto; background: #fff; border-radius: 24px;
          padding: 28px 22px; box-shadow: 0 8px 30px rgba(0,0,0,0.08); }
  .eyebrow { font-size: 11px; letter-spacing: 1.5px; color: #F97316; font-weight: 700; text-transform: uppercase; }
  h1 { font-size: 22px; margin: 8px 0 4px; }
  .meta { color: #666; font-size: 14px; margin-bottom: 20px; line-height: 1.6; }
  .status { display: inline-block; padding: 6px 14px; border-radius: 20px; font-size: 12px;
            font-weight: 700; background: #FFF0DE; color: #F97316; margin-bottom: 16px; }
  .btns { display: flex; flex-direction: column; gap: 10px; margin-top: 16px; }
  button { padding: 14px; border-radius: 14px; border: 1.5px solid #eee; background: #fff;
           font-size: 15px; font-weight: 700; cursor: pointer; }
  button.primary { background: #F97316; color: #fff; border: none; }
  button:disabled { opacity: 0.5; cursor: not-allowed; }
  .note { font-size: 13px; color: #999; margin-top: 18px; text-align: center; }
  .error { color: #E11D48; font-size: 14px; }
  .thanks { text-align: center; padding: 20px 0; }
</style>
</head>
<body>
  <div class="card" id="app">Loading…</div>
  <script>
    const token = window.location.pathname.split('/').filter(Boolean).slice(-2, -1)[0];
    const apiBase = window.location.origin + '/api/v1/public/rsvp/' + token;

    async function load() {
      try {
        const res = await fetch(apiBase);
        const body = await res.json();
        if (!res.ok) throw new Error(body.message || 'This invite link is invalid or has expired.');
        render(body.data);
      } catch (e) {
        document.getElementById('app').innerHTML = '<p class="error">' + e.message + '</p>';
      }
    }

    function render(data) {
      const statusLabel = { attending: "You're coming!", maybe: "You said maybe", declined: "You can't make it" }[data.rsvp_status];
      const el = document.getElementById('app');
      el.innerHTML =
        '<div class="eyebrow">You\\'re invited</div>' +
        '<h1>' + data.celebration_title + '</h1>' +
        '<div class="meta">' + data.celebration_date +
        (data.venue_name ? ' · ' + data.venue_name : '') +
        (data.venue_address ? '<br>' + data.venue_address : '') + '</div>' +
        (statusLabel ? '<div class="status">' + statusLabel + '</div>' : '') +
        (data.can_still_respond
          ? '<div class="btns">' +
            '<button class="primary" onclick="submitRsvp(\\'attending\\')">I\\'m coming 🎉</button>' +
            '<button onclick="submitRsvp(\\'maybe\\')">Maybe</button>' +
            '<button onclick="submitRsvp(\\'declined\\')">Can\\'t make it</button>' +
            '</div>' +
            '<div class="note">Hi ' + data.guest_name + ' — you can change your response any time before the event.</div>'
          : '<div class="note">The RSVP window for this event has closed.</div>');
    }

    async function submitRsvp(status) {
      try {
        const res = await fetch(apiBase, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ rsvp_status: status }),
        });
        const body = await res.json();
        if (!res.ok) throw new Error(body.message || 'Could not save your response.');
        document.getElementById('app').innerHTML = '<div class="thanks"><h1>Thanks!</h1><p class="meta">Your response has been recorded.</p></div>';
      } catch (e) {
        alert(e.message);
      }
    }

    load();
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)


# ── Checklist ──────────────────────────────────────────────────────────────────

async def add_checklist_item(
    celebration_id: uuid.UUID,
    body: CelebrationChecklistCreate,
    current_user: CurrentUserDep,
    service: OccasionServiceDep,
) -> SuccessResponse[CelebrationChecklistResponse]:
    result = await service.add_checklist_item(
        celebration_id=celebration_id, user_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Checklist item added.")


async def update_checklist_item(
    celebration_id: uuid.UUID,
    item_id: uuid.UUID,
    body: CelebrationChecklistUpdate,
    current_user: CurrentUserDep,
    service: OccasionServiceDep,
) -> SuccessResponse[CelebrationChecklistResponse]:
    result = await service.update_checklist_item(
        celebration_id=celebration_id, item_id=item_id, user_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Checklist item updated.")


async def delete_checklist_item(
    celebration_id: uuid.UUID,
    item_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: OccasionServiceDep,
) -> SuccessResponse[None]:
    await service.delete_checklist_item(
        celebration_id=celebration_id, item_id=item_id, user_id=current_user.id
    )
    return SuccessResponse(data=None, message="Checklist item deleted.")


async def list_checklist(
    celebration_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: OccasionServiceDep,
) -> SuccessResponse[list[CelebrationChecklistResponse]]:
    items = await service.list_checklist(
        celebration_id=celebration_id, user_id=current_user.id
    )
    return SuccessResponse(data=items, message="Checklist retrieved.")


async def get_checklist_progress(
    celebration_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: OccasionServiceDep,
) -> SuccessResponse[dict]:
    progress = await service.get_checklist_progress(
        celebration_id=celebration_id, user_id=current_user.id
    )
    return SuccessResponse(data=progress, message="Checklist progress retrieved.")


# ── Timeline ───────────────────────────────────────────────────────────────────

async def add_timeline_event(
    celebration_id: uuid.UUID,
    body: CelebrationTimelineCreate,
    current_user: CurrentUserDep,
    service: OccasionServiceDep,
) -> SuccessResponse[CelebrationTimelineResponse]:
    result = await service.add_timeline_event(
        celebration_id=celebration_id, user_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Timeline event added.")


async def update_timeline_event(
    celebration_id: uuid.UUID,
    event_id: uuid.UUID,
    body: CelebrationTimelineUpdate,
    current_user: CurrentUserDep,
    service: OccasionServiceDep,
) -> SuccessResponse[CelebrationTimelineResponse]:
    result = await service.update_timeline_event(
        celebration_id=celebration_id, event_id=event_id, user_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Timeline event updated.")


async def delete_timeline_event(
    celebration_id: uuid.UUID,
    event_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: OccasionServiceDep,
) -> SuccessResponse[None]:
    await service.delete_timeline_event(
        celebration_id=celebration_id, event_id=event_id, user_id=current_user.id
    )
    return SuccessResponse(data=None, message="Timeline event deleted.")


async def list_timeline(
    celebration_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: OccasionServiceDep,
) -> SuccessResponse[list[CelebrationTimelineResponse]]:
    events = await service.list_timeline(
        celebration_id=celebration_id, user_id=current_user.id
    )
    return SuccessResponse(data=events, message="Timeline retrieved.")


# ── Notes ──────────────────────────────────────────────────────────────────────

async def add_note(
    celebration_id: uuid.UUID,
    body: CelebrationNoteCreate,
    current_user: CurrentUserDep,
    service: OccasionServiceDep,
) -> SuccessResponse[CelebrationNoteResponse]:
    result = await service.add_note(
        celebration_id=celebration_id, user_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Note added.")


async def update_note(
    celebration_id: uuid.UUID,
    note_id: uuid.UUID,
    body: CelebrationNoteUpdate,
    current_user: CurrentUserDep,
    service: OccasionServiceDep,
) -> SuccessResponse[CelebrationNoteResponse]:
    result = await service.update_note(
        celebration_id=celebration_id, note_id=note_id, user_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Note updated.")


async def delete_note(
    celebration_id: uuid.UUID,
    note_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: OccasionServiceDep,
) -> SuccessResponse[None]:
    await service.delete_note(
        celebration_id=celebration_id, note_id=note_id, user_id=current_user.id
    )
    return SuccessResponse(data=None, message="Note deleted.")


async def list_notes(
    celebration_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: OccasionServiceDep,
) -> SuccessResponse[list[CelebrationNoteResponse]]:
    notes = await service.list_notes(
        celebration_id=celebration_id, user_id=current_user.id
    )
    return SuccessResponse(data=notes, message="Notes retrieved.")
