"""Auth domain models — OTP records, refresh tokens, user sessions.

Every model must be re-exported here: `app/models/__init__.py` imports this
package and nothing else from the domain, so a module left out never reaches
Base.metadata — alembic autogenerate would then propose dropping its table.
"""

from app.models.auth.otp import OTPRecord
from app.models.auth.refresh_token import RefreshToken
from app.models.auth.session import UserSession

__all__ = [
    "OTPRecord",
    "RefreshToken",
    "UserSession",
]
