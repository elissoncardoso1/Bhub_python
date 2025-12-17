"""
Exceções customizadas da aplicação.
"""

from typing import Any

from fastapi import HTTPException, status


class BHUBException(Exception):
    """Exceção base da aplicação."""

    def __init__(self, message: str, code: str | None = None):
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(BHUBException):
    """Recurso não encontrado."""

    def __init__(self, resource: str, identifier: Any = None):
        message = f"{resource} não encontrado"
        if identifier:
            message = f"{resource} com id '{identifier}' não encontrado"
        super().__init__(message, "NOT_FOUND")


class DuplicateError(BHUBException):
    """Recurso duplicado."""

    def __init__(self, resource: str, field: str = ""):
        message = f"{resource} já existe"
        if field:
            message = f"{resource} com {field} já existe"
        super().__init__(message, "DUPLICATE")


class ValidationError(BHUBException):
    """Erro de validação."""

    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")


class AuthenticationError(BHUBException):
    """Erro de autenticação."""

    def __init__(self, message: str = "Credenciais inválidas"):
        super().__init__(message, "AUTHENTICATION_ERROR")


class AuthorizationError(BHUBException):
    """Erro de autorização."""

    def __init__(self, message: str = "Acesso negado"):
        super().__init__(message, "AUTHORIZATION_ERROR")


class ExternalServiceError(BHUBException):
    """Erro em serviço externo."""

    def __init__(self, service: str, message: str = ""):
        full_message = f"Erro no serviço {service}"
        if message:
            full_message = f"{full_message}: {message}"
        super().__init__(full_message, "EXTERNAL_SERVICE_ERROR")


class RateLimitError(BHUBException):
    """Limite de requisições excedido."""

    def __init__(self, message: str = "Limite de requisições excedido"):
        super().__init__(message, "RATE_LIMIT_ERROR")


class PDFProcessingError(BHUBException):
    """Erro no processamento de PDF."""

    def __init__(self, message: str):
        super().__init__(message, "PDF_PROCESSING_ERROR")


class FeedSyncError(BHUBException):
    """Erro na sincronização de feed."""

    def __init__(self, feed_name: str, message: str = ""):
        full_message = f"Erro ao sincronizar feed '{feed_name}'"
        if message:
            full_message = f"{full_message}: {message}"
        super().__init__(full_message, "FEED_SYNC_ERROR")


class MLClassificationError(BHUBException):
    """Erro na classificação ML."""

    def __init__(self, message: str = "Erro na classificação"):
        super().__init__(message, "ML_CLASSIFICATION_ERROR")


# HTTP Exceptions helpers
def not_found_exception(resource: str, identifier: Any = None) -> HTTPException:
    """Cria HTTPException 404."""
    message = f"{resource} não encontrado"
    if identifier:
        message = f"{resource} com id '{identifier}' não encontrado"
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)


def bad_request_exception(message: str) -> HTTPException:
    """Cria HTTPException 400."""
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


def unauthorized_exception(message: str = "Não autorizado") -> HTTPException:
    """Cria HTTPException 401."""
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)


def forbidden_exception(message: str = "Acesso negado") -> HTTPException:
    """Cria HTTPException 403."""
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)


def conflict_exception(message: str) -> HTTPException:
    """Cria HTTPException 409."""
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)


def internal_error_exception(message: str = "Erro interno") -> HTTPException:
    """Cria HTTPException 500."""
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)
