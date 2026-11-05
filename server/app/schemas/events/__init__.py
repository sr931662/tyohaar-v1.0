"""
Event & invitation-management schemas.

An "event" is a Celebration seen through the invitation-management lens; these
shapes add to the existing invitation schemas rather than replace them.

Two audiences, kept strictly apart:

* **Organiser** (owner, authenticated) — everything below except ``Public*``.
* **Guest** (by link token) — only ``Public*``. These contain the guest's own
  invitation and the event basics: never another guest's contact details, never
  the host's account, never internal ids beyond the ones needed to answer.
"""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.models.enums import GuestGroupResponseMode, RSVPStatus
from app.schemas.base import BaseSchema
from app.schemas.invitations import InvitationSummary

EVENT_TYPES: dict[str, str] = {
    "wedding": "Wedding",
    "birthday": "Birthday",
    "anniversary": "Anniversary",
    "engagement": "Engagement",
    "baby_shower": "Baby Shower",
    "housewarming": "Housewarming",
    "religious": "Religious Celebration",
    "corporate": "Corporate Event",
    "custom": "Custom Event",
}
DIETARY_TYPES = ("vegetarian", "non_vegetarian", "jain", "vegan", "other")
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _clean(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


# ── Invitation settings (stored as JSON on the celebration) ───────────────────

class InvitationDesign(BaseSchema):
    template: Literal["classic", "royal", "floral", "minimal"] = "classic"
    font: Literal["serif", "modern", "traditional"] = "serif"
    primary_color: str = "#5B1226"
    accent_color: str = "#B8892F"
    background_color: str = "#FBF6EC"
    heading: str | None = Field(default=None, max_length=120)
    tagline: str | None = Field(default=None, max_length=60, description="Short ribbon line, e.g. 'Turning 5!'.")
    message: str | None = Field(default=None, max_length=1500)

    @field_validator("primary_color", "accent_color", "background_color")
    @classmethod
    def _hex(cls, v: str) -> str:
        # These end up inside a <style> block on a public page.
        if not _HEX.match(v):
            raise ValueError("Colours must look like #RRGGBB.")
        return v

    _strip = field_validator("heading", "tagline", "message", mode="before")(_clean)


class RSVPQuestion(BaseSchema):
    id: str = Field(min_length=1, max_length=40, pattern=r"^[a-zA-Z0-9_-]+$")
    label: str = Field(min_length=1, max_length=200)
    kind: Literal["text", "choice", "yes_no"] = "text"
    options: list[str] = Field(default_factory=list, max_length=20)
    required: bool = False

    @model_validator(mode="after")
    def _choice_has_options(self):
        if self.kind == "choice" and not self.options:
            raise ValueError("A multiple-choice question needs at least one option.")
        return self


class RSVPSettings(BaseSchema):
    allow_maybe: bool = True
    allow_edit: bool = True
    ask_attendee_count: bool = True
    ask_food: bool = False
    ask_allergies: bool = False
    ask_special_requirements: bool = False
    meal_options: list[str] = Field(default_factory=list, max_length=20)
    deadline: date | None = None
    questions: list[RSVPQuestion] = Field(default_factory=list, max_length=20)

    @field_validator("questions")
    @classmethod
    def _unique_ids(cls, v: list[RSVPQuestion]) -> list[RSVPQuestion]:
        if len({q.id for q in v}) != len(v):
            raise ValueError("Each question needs its own id.")
        return v


class InvitationDisplay(BaseSchema):
    """
    What guests see, where it differs from the event record. This is how a
    booked customer adjusts their invitation without touching the booking.
    """

    title: str | None = Field(default=None, max_length=300)
    venue_name: str | None = Field(default=None, max_length=300)
    venue_address: str | None = Field(default=None, max_length=1000)
    start_time: time | None = None
    instructions: str | None = Field(default=None, max_length=2000)

    _strip = field_validator("title", "venue_name", "venue_address", "instructions", mode="before")(_clean)


class ReminderRules(BaseSchema):
    """Days to wait; None turns a rule off. Responded or declined guests never qualify."""

    after_visit_no_rsvp_days: int | None = Field(default=2, ge=1, le=60)
    not_responded_days: int | None = Field(default=5, ge=1, le=60)
    final_before_deadline_days: int | None = Field(default=2, ge=1, le=60)


class GeneralLinkSettings(BaseSchema):
    enabled: bool = False
    plus_ones_allowed: int = Field(default=0, ge=0, le=20)


class InvitationSettings(BaseSchema):
    invitation_type: Literal["web", "static"] = "web"
    design: InvitationDesign = Field(default_factory=InvitationDesign)
    rsvp: RSVPSettings = Field(default_factory=RSVPSettings)
    display: InvitationDisplay = Field(default_factory=InvitationDisplay)
    reminders: ReminderRules = Field(default_factory=ReminderRules)
    general_link: GeneralLinkSettings = Field(default_factory=GeneralLinkSettings)


# ── Functions ─────────────────────────────────────────────────────────────────

class FunctionFields(BaseSchema):
    venue_name: str | None = Field(default=None, max_length=300)
    venue_address: str | None = Field(default=None, max_length=1000)
    map_url: str | None = Field(default=None, max_length=1000)
    description: str | None = Field(default=None, max_length=2000)
    dress_code: str | None = Field(default=None, max_length=200)
    start_time: time | None = None
    end_time: time | None = None

    _strip = field_validator("venue_name", "venue_address", "map_url", "description", "dress_code", mode="before")(_clean)

    @field_validator("map_url")
    @classmethod
    def _http_only(cls, v: str | None) -> str | None:
        # Rendered as a link on a public page; no javascript: URLs.
        if v and not v.lower().startswith(("https://", "http://")):
            raise ValueError("Map link must start with https://")
        return v


class FunctionCreate(FunctionFields):
    name: str = Field(min_length=1, max_length=120)
    function_date: date
    invite_all_guests: bool = Field(default=True, description="Invite everyone already on the list.")


class FunctionUpdate(FunctionFields):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    function_date: date | None = None
    is_cancelled: bool | None = None


class FunctionReorder(BaseSchema):
    function_ids: list[uuid.UUID] = Field(min_length=1, max_length=50)


class FunctionResponse(BaseSchema):
    id: uuid.UUID
    celebration_id: uuid.UUID
    name: str
    function_date: date
    start_time: time | None = None
    end_time: time | None = None
    venue_name: str | None = None
    venue_address: str | None = None
    map_url: str | None = None
    description: str | None = None
    dress_code: str | None = None
    display_order: int
    is_cancelled: bool


class GuestFunctionsUpdate(BaseSchema):
    guest_ids: list[uuid.UUID] = Field(min_length=1, max_length=1000)
    function_ids: list[uuid.UUID] = Field(min_length=1, max_length=50)


# ── Households ────────────────────────────────────────────────────────────────

class GuestGroupCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    invitation_capacity: int | None = Field(default=None, ge=1, le=100)
    response_mode: GuestGroupResponseMode = GuestGroupResponseMode.GROUP
    guest_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)
    primary_guest_id: uuid.UUID | None = None


class GuestGroupUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    invitation_capacity: int | None = Field(default=None, ge=1, le=100)
    response_mode: GuestGroupResponseMode | None = None
    guest_ids: list[uuid.UUID] | None = Field(default=None, max_length=100)
    primary_guest_id: uuid.UUID | None = None


class GuestGroupMember(BaseSchema):
    id: uuid.UUID
    name: str
    plus_ones_allowed: int


class GuestGroupResponse(BaseSchema):
    id: uuid.UUID
    celebration_id: uuid.UUID
    name: str
    category: str | None = None
    invitation_capacity: int | None = None
    response_mode: GuestGroupResponseMode
    primary_guest_id: uuid.UUID | None = None
    members: list[GuestGroupMember] = []
    invite_url: str | None = Field(default=None, description="The primary guest's link, which opens the whole household.")


# ── Event ─────────────────────────────────────────────────────────────────────

class EventCreate(BaseSchema):
    """An independently organised event. No booking anywhere in this path."""

    title: str = Field(min_length=1, max_length=300)
    event_type: str
    custom_event_type: str | None = Field(default=None, max_length=80)
    host_name: str | None = Field(default=None, max_length=200)
    celebration_date: date
    start_time: time | None = None
    end_time: time | None = None
    venue_name: str | None = Field(default=None, max_length=300)
    venue_address: str | None = Field(default=None, max_length=1000)
    description: str | None = Field(default=None, max_length=4000)
    cover_image_url: str | None = Field(default=None, max_length=1000)
    contact_name: str | None = Field(default=None, max_length=200)
    contact_phone: str | None = Field(default=None, max_length=20)
    functions: list[FunctionCreate] = Field(default_factory=list, max_length=30)
    client_request_id: str | None = Field(default=None, min_length=8, max_length=64)

    _strip = field_validator(
        "custom_event_type", "host_name", "venue_name", "venue_address", "description",
        "cover_image_url", "contact_name", "contact_phone", mode="before",
    )(_clean)

    @field_validator("event_type")
    @classmethod
    def _known_type(cls, v: str) -> str:
        if v not in EVENT_TYPES:
            raise ValueError("Choose one of the event categories.")
        return v

    @model_validator(mode="after")
    def _custom_named(self):
        if self.event_type == "custom" and not self.custom_event_type:
            raise ValueError("Tell us what kind of event this is.")
        return self


class EventUpdate(BaseSchema):
    """Fields a booked event refuses (date, venue) are rejected by the service, not here."""

    title: str | None = Field(default=None, min_length=1, max_length=300)
    event_type: str | None = None
    custom_event_type: str | None = Field(default=None, max_length=80)
    host_name: str | None = Field(default=None, max_length=200)
    celebration_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    venue_name: str | None = Field(default=None, max_length=300)
    venue_address: str | None = Field(default=None, max_length=1000)
    description: str | None = Field(default=None, max_length=4000)
    cover_image_url: str | None = Field(default=None, max_length=1000)
    contact_name: str | None = Field(default=None, max_length=200)
    contact_phone: str | None = Field(default=None, max_length=20)

    @field_validator("event_type")
    @classmethod
    def _known_type(cls, v: str | None) -> str | None:
        if v is not None and v not in EVENT_TYPES:
            raise ValueError("Choose one of the event categories.")
        return v


class EventCounts(BaseSchema):
    invited: int = 0
    confirmed: int = 0
    maybe: int = 0
    declined: int = 0
    pending: int = 0


class EventCard(BaseSchema):
    id: uuid.UUID
    title: str
    event_type: str | None = None
    event_type_label: str
    cover_image_url: str | None = None
    celebration_date: date
    end_date: date | None = None
    start_time: time | None = None
    venue_name: str | None = None
    venue_address: str | None = None
    status: str
    segment: Literal["upcoming", "ongoing", "completed"]
    days_remaining: int | None = None
    event_source: str
    booking_id: uuid.UUID | None = None
    booking_status: str | None = None
    function_count: int = 0
    invitation_status: str
    invitations_configured: bool = False
    counts: EventCounts = Field(default_factory=EventCounts)


class EventList(BaseSchema):
    upcoming: list[EventCard]
    ongoing: list[EventCard]
    completed: list[EventCard]


class Entitlements(BaseSchema):
    invitation_management: bool = True
    guest_management: bool = True
    custom_templates: bool = True
    advanced_rsvp: bool = True
    food_preferences: bool = True
    qr_check_in: bool = True
    automated_reminders: bool = False
    vendor_reports: bool = False
    advanced_analytics: bool = True


class BookingInfo(BaseSchema):
    booking_id: uuid.UUID
    booking_number: str | None = None
    status: str
    package_name: str | None = None
    package_cover_url: str | None = None
    scheduled_date: date | None = None


class EventDetail(EventCard):
    description: str | None = None
    host_name: str | None = None
    custom_event_type: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    end_time: time | None = None
    settings: InvitationSettings
    functions: list[FunctionResponse] = []
    groups: list[GuestGroupResponse] = []
    entitlements: Entitlements
    booking: BookingInfo | None = None
    general_link_url: str | None = None
    invitation_published_at: datetime | None = None
    operations_summary: dict | None = None
    # Date and venue come from the booking on a booked event.
    locked_fields: list[str] = []


class InvitationSettingsUpdate(BaseSchema):
    invitation_type: Literal["web", "static"] | None = None
    design: InvitationDesign | None = None
    rsvp: RSVPSettings | None = None
    display: InvitationDisplay | None = None
    reminders: ReminderRules | None = None


class GeneralLinkUpdate(BaseSchema):
    enabled: bool
    plus_ones_allowed: int | None = Field(default=None, ge=0, le=20)
    rotate: bool = False


class PreviewLink(BaseSchema):
    url: str
    expires_at: datetime


# ── Analytics ─────────────────────────────────────────────────────────────────

class FunctionStats(BaseSchema):
    function_id: uuid.UUID | None = None
    name: str
    function_date: date | None = None
    is_cancelled: bool = False
    invited: int = 0
    confirmed: int = 0
    maybe: int = 0
    declined: int = 0
    pending: int = 0
    confirmed_people: int = 0


class EventAnalytics(BaseSchema):
    summary: InvitationSummary
    invitations_generated: int
    shared: int
    link_accessed: int
    qualified_visits: int
    rsvp_started: int
    responded: int
    pending: int
    confirmed: int
    declined: int
    maybe: int
    response_rate: float = Field(description="Guests who answered in any way, as a share of active invitations (0-1).")
    confirmation_rate: float = Field(description="Guests who said they're coming, as a share of active invitations (0-1).")
    general_link_visits: int
    functions: list[FunctionStats]


class ActivityItem(BaseSchema):
    id: uuid.UUID
    guest_id: uuid.UUID
    guest_name: str
    event_type: str
    previous_status: RSVPStatus | None = None
    new_status: RSVPStatus | None = None
    actor_type: str | None = None
    function_name: str | None = None
    channel: str | None = None
    is_update: bool = False
    occurred_at: datetime


class RSVPRow(BaseSchema):
    guest_id: uuid.UUID
    guest_name: str
    group_name: str | None = None
    function_id: uuid.UUID | None = None
    function_name: str | None = None
    status: RSVPStatus
    attendee_count: int | None = None
    dietary_type: str | None = None
    meal_selection: str | None = None
    allergies: str | None = None
    special_requirements: str | None = None
    answers: dict | None = None
    responded_at: datetime | None = None


class FoodFunctionSummary(BaseSchema):
    function_id: uuid.UUID | None = None
    name: str
    people: int = 0
    dietary: dict[str, int] = {}
    meals: dict[str, int] = {}
    not_specified: int = 0
    with_allergies: int = 0


class FoodSummary(BaseSchema):
    enabled: bool
    functions: list[FoodFunctionSummary]


class ReminderCandidate(BaseSchema):
    guest_id: uuid.UUID
    guest_name: str
    phone: str | None = None
    invite_url: str | None = None
    reasons: list[str]
    reminder_count: int = 0
    last_reminded_at: datetime | None = None


class ReminderCandidates(BaseSchema):
    automated_available: bool
    rules: ReminderRules
    candidates: list[ReminderCandidate]


class ReminderRecord(BaseSchema):
    guest_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)
    channel: Literal["share_sheet", "whatsapp", "copy_link", "sms", "email"]


class ImportRowResult(BaseSchema):
    row: int
    status: Literal["created", "existing", "duplicate", "error"]
    name: str | None = None
    message: str | None = None


class ImportResult(BaseSchema):
    created: int
    skipped: int
    groups_created: int = 0
    rows: list[ImportRowResult]


class OperationsApproval(BaseSchema):
    final_guest_count: int | None = Field(default=None, ge=0, le=100000)
    note: str | None = Field(default=None, max_length=500)


class VendorGuestSummary(BaseSchema):
    """Aggregates only. A vendor never receives a guest's name or number."""

    approved_at: datetime
    final_guest_count: int | None = None
    note: str | None = None
    functions: list[FoodFunctionSummary]


# ── Guest (public) ────────────────────────────────────────────────────────────

class PublicFunction(BaseSchema):
    id: uuid.UUID
    name: str
    function_date: date
    start_time: time | None = None
    end_time: time | None = None
    venue_name: str | None = None
    venue_address: str | None = None
    map_url: str | None = None
    description: str | None = None
    dress_code: str | None = None
    is_open: bool = True
    is_cancelled: bool = False


class PublicMemberResponse(BaseSchema):
    function_id: uuid.UUID | None = None
    status: RSVPStatus
    attendee_count: int | None = None
    dietary_type: str | None = None
    meal_selection: str | None = None
    allergies: str | None = None
    special_requirements: str | None = None
    answers: dict | None = None


class PublicMember(BaseSchema):
    id: uuid.UUID
    name: str
    plus_ones_allowed: int
    is_self: bool = False
    function_ids: list[uuid.UUID] = []
    responses: list[PublicMemberResponse] = []


class PublicPass(BaseSchema):
    name: str
    entry_code: str
    qr_svg: str


class PublicRSVPConfig(BaseSchema):
    allow_maybe: bool
    allow_edit: bool
    ask_attendee_count: bool
    ask_food: bool
    ask_allergies: bool
    ask_special_requirements: bool
    meal_options: list[str]
    questions: list[RSVPQuestion]
    deadline: date | None = None


class PublicEvent(BaseSchema):
    """What a guest sees. Host contact appears only if the host provided one for this purpose."""

    title: str
    event_type_label: str
    host_name: str | None = None
    heading: str | None = None
    message: str | None = None
    instructions: str | None = None
    cover_image_url: str | None = None
    celebration_date: date
    end_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    venue_name: str | None = None
    venue_address: str | None = None
    map_url: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    design: InvitationDesign
    status: str
    website_url: str
    android_app_url: str | None = None
    ios_app_url: str | None = None


class PublicInvitationPage(BaseSchema):
    kind: Literal["personal", "general", "preview"]
    event: PublicEvent
    functions: list[PublicFunction] = []
    members: list[PublicMember] = []
    response_mode: Literal["single", "group", "individual"] = "single"
    capacity: int = 1
    rsvp: PublicRSVPConfig
    can_respond: bool = False
    closed_reason: str | None = None
    has_responded: bool = False
    guest_note: str | None = None
    pass_state: str | None = None
    passes: list[PublicPass] = []
    general_plus_ones: int = 0


class PublicResponseItem(BaseSchema):
    guest_id: uuid.UUID | None = Field(default=None, description="Household member; omitted means the link holder.")
    function_id: uuid.UUID | None = None
    status: RSVPStatus
    attendee_count: int | None = Field(default=None, ge=1, le=100)
    dietary_type: str | None = None
    meal_selection: str | None = Field(default=None, max_length=120)
    allergies: str | None = Field(default=None, max_length=500)
    special_requirements: str | None = Field(default=None, max_length=1000)
    answers: dict[str, str] | None = None

    _strip = field_validator("dietary_type", "meal_selection", "allergies", "special_requirements", mode="before")(_clean)

    @field_validator("status")
    @classmethod
    def _guest_choosable(cls, v: RSVPStatus) -> RSVPStatus:
        if v not in (RSVPStatus.ATTENDING, RSVPStatus.MAYBE, RSVPStatus.DECLINED):
            raise ValueError("Choose attending, maybe or declined.")
        return v

    @field_validator("answers")
    @classmethod
    def _bounded(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        if v is not None and (len(v) > 20 or any(len(a) > 1000 for a in v.values())):
            raise ValueError("Those answers are too long.")
        return v


class PublicRSVPRequest(BaseSchema):
    responses: list[PublicResponseItem] = Field(min_length=1, max_length=500)
    note: str | None = Field(default=None, max_length=1000)


class PublicClaim(BaseSchema):
    """A visitor to the general link identifying themselves."""

    name: str = Field(min_length=2, max_length=200)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=320)
    # Bots fill every field; people never see this one.
    website: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _contact(self):
        if not (self.phone or "").strip() and not (self.email or "").strip():
            raise ValueError("Give a mobile number or email so the host knows it's you.")
        return self


class PublicClaimResult(BaseSchema):
    url: str
    token: str


class PublicActivity(BaseSchema):
    type: Literal["rsvp_started"]
