"""
Central SQLAlchemy declarative base for all Tyohaar ORM models.

Every model in this project must inherit from `Base` defined here.
This supersedes `app/db/base.py` for all new models going forward.

Alembic's env.py should import `Base.metadata` from this module and
import every model sub-package so autogenerate can detect all tables.
"""

import re

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, declared_attr

# ──────────────────────────────────────────────────────────────────────────────
# Constraint naming convention
#
# Required by Alembic to produce stable, deterministic migration names for
# indexes, unique constraints, foreign keys, check constraints, and primary keys.
# Without this, Alembic uses DB-generated names which differ across environments.
# ──────────────────────────────────────────────────────────────────────────────
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """
    Project-wide SQLAlchemy 2.0 declarative base.

    Key characteristics:
    - Named constraint conventions for clean Alembic autogenerate output.
    - Automatic snake_case table naming derived from class name (overridable).
    - Fully async-compatible via SQLAlchemy's async extension.
    - Relationship-ready: does not use lazy="dynamic" anywhere, which is
      incompatible with async sessions. Use selectin or joined loading instead.
    - No business columns here — only structural ORM configuration.

    Recommended model declaration:

        class Booking(UUIDPrimaryKeyMixin, TimestampMixin, Base):
            __tablename__ = "bookings"

            # columns ...
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Derive a snake_case table name from the class name.

        Handles standard CamelCase and acronym-prefixed names:
            UserSession  → user_session
            OTPRecord    → otp_record
            RefreshToken → refresh_token
            HTTPSConfig  → https_config

        Models should override __tablename__ explicitly when a different
        name is required (e.g., plural forms, abbreviations).
        """
        # Step 1: Insert underscore between a run of capitals and a capital+lowercase
        # e.g. "OTPRecord" → "OTP_Record"
        s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", cls.__name__)
        # Step 2: Insert underscore between lowercase/digit and an uppercase letter
        # e.g. "OTP_Record" → "OTP_Record", "UserSession" → "User_Session"
        s2 = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s1)
        return s2.lower()
