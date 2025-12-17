"""
Módulo core da aplicação.
"""

from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    BHUBException,
    DuplicateError,
    ExternalServiceError,
    FeedSyncError,
    MLClassificationError,
    NotFoundError,
    PDFProcessingError,
    RateLimitError,
    ValidationError,
    bad_request_exception,
    conflict_exception,
    forbidden_exception,
    internal_error_exception,
    not_found_exception,
    unauthorized_exception,
)
from app.core.logging import get_logger, log, setup_logging
from app.core.security import (
    CurrentAdmin,
    CurrentSuperuser,
    CurrentUser,
    auth_backend,
    current_admin_user,
    current_superuser,
    current_user,
    fastapi_users,
    get_jwt_strategy,
    get_user_db,
    get_user_manager,
)

__all__ = [
    # Logging
    "setup_logging",
    "get_logger",
    "log",
    # Security
    "fastapi_users",
    "auth_backend",
    "get_jwt_strategy",
    "get_user_db",
    "get_user_manager",
    "current_user",
    "current_admin_user",
    "current_superuser",
    "CurrentUser",
    "CurrentAdmin",
    "CurrentSuperuser",
    # Exceptions
    "BHUBException",
    "NotFoundError",
    "DuplicateError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "ExternalServiceError",
    "RateLimitError",
    "PDFProcessingError",
    "FeedSyncError",
    "MLClassificationError",
    "not_found_exception",
    "bad_request_exception",
    "unauthorized_exception",
    "forbidden_exception",
    "conflict_exception",
    "internal_error_exception",
]
