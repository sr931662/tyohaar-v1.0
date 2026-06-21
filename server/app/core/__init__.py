"""
Tyohaar Core Infrastructure Layer
==================================

Provides all DI wiring, configuration, database access, security utilities,
and error handling for the API. Import directly from submodules:

    from app.core.config import settings
    from app.core.dependencies import AuthServiceDep, UoWDep
    from app.core.current_user import CurrentUserDep
    from app.core.permissions import AdminDep, require_roles
    from app.core.pagination import get_offset_pagination
    from app.core.responses import PaginatedResponse, SuccessResponse
    from app.core.exceptions import register_exception_handlers
    from app.core.lifespan import lifespan
"""
