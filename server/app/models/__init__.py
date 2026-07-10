# Import every domain package so SQLAlchemy Base.metadata is fully populated.
# Alembic's env.py does `import app.models` — all models must be reachable here.

import app.models.admin          # noqa: F401
import app.models.auth           # noqa: F401
import app.models.bookings       # noqa: F401
import app.models.budgets        # noqa: F401
import app.models.common         # noqa: F401
import app.models.feedback       # noqa: F401
import app.models.invitations    # noqa: F401
import app.models.media          # noqa: F401
import app.models.memberships    # noqa: F401
import app.models.notifications  # noqa: F401
import app.models.occasions      # noqa: F401
import app.models.packages       # noqa: F401
import app.models.payments       # noqa: F401
import app.models.referrals      # noqa: F401
import app.models.support        # noqa: F401
import app.models.users          # noqa: F401
import app.models.vendors        # noqa: F401
