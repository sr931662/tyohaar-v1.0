"""
Enum storage contract.

SQLAlchemy's `Enum` type persists the member **name**, not the member value —
`DeletionRequestStatus.RECOVERABLE` lands in the column as `'RECOVERABLE'`,
never `'recoverable'`. Anything written in raw SQL against these columns has to
agree with that, and nothing about the Python code makes the mismatch visible:
a predicate written against the lowercase value simply matches zero rows, so a
unique index silently stops constraining and a filter silently returns nothing.

This is the failure that motivated the test. It cannot be caught by reading the
model.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.models.enums import DeletionRequestChannel, DeletionRequestStatus
from app.models.users.deletion_request import DeletionRequest

MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations/versions/9b2e8c4d3f51_account_deletion_pipeline.py"
)


def _stored(column, member):
    """What actually reaches the database for this enum member."""
    processor = column.type.bind_processor(None) or (lambda v: v)
    return processor(member)


def test_status_column_stores_member_names():
    column = DeletionRequest.__table__.c.status
    assert _stored(column, DeletionRequestStatus.RECOVERABLE) == "RECOVERABLE"
    assert _stored(column, DeletionRequestStatus.PURGED) == "PURGED"


def test_channel_column_stores_member_names():
    column = DeletionRequest.__table__.c.channel
    assert _stored(column, DeletionRequestChannel.IN_APP) == "IN_APP"


def test_partial_index_predicate_matches_what_is_stored():
    """The live-request unique index must actually constrain something.

    If this fails the index still exists and still reports as created — it just
    never matches a row, so a user could hold several concurrent deletion
    requests and nothing would complain.
    """
    source = MIGRATION.read_text(encoding="utf-8")
    predicate = re.search(r"status IN \(([^)]*)\)", source)
    assert predicate, "live-request partial index predicate not found"

    literals = set(re.findall(r"'([^']+)'", predicate.group(1)))
    column = DeletionRequest.__table__.c.status

    expected = {
        _stored(column, member)
        for member in (
            DeletionRequestStatus.PENDING_VERIFICATION,
            DeletionRequestStatus.RECOVERABLE,
            DeletionRequestStatus.PURGING,
        )
    }

    assert literals == expected, (
        f"index predicate uses {sorted(literals)} but the column stores "
        f"{sorted(expected)} — the constraint would never fire"
    )


def test_no_lowercase_enum_literals_in_the_deletion_migration():
    """Guard against the same slip being reintroduced elsewhere in the file."""
    source = MIGRATION.read_text(encoding="utf-8")
    for match in re.finditer(r"status IN \(([^)]*)\)", source):
        for literal in re.findall(r"'([^']+)'", match.group(1)):
            assert literal.isupper(), (
                f"{literal!r} is a lowercase enum value; SQLAlchemy stores "
                "member names, so this predicate matches nothing"
            )
