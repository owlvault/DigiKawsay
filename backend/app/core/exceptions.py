"""Custom application exceptions."""

from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base application exception."""
    def __init__(self, detail: str, status_code: int = 500):
        super().__init__(status_code=status_code, detail=detail)


class AuthenticationError(AppException):
    """Authentication failed."""
    def __init__(self, detail: str = "Credenciales inválidas"):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(AppException):
    """User not authorized."""
    def __init__(self, detail: str = "Sin permisos para esta acción"):
        super().__init__(detail=detail, status_code=status.HTTP_403_FORBIDDEN)


class NotFoundError(AppException):
    """Resource not found."""
    def __init__(self, resource: str = "Recurso"):
        super().__init__(
            detail=f"{resource} no encontrado",
            status_code=status.HTTP_404_NOT_FOUND
        )


class ValidationError(AppException):
    """Validation error."""
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)


class RateLimitError(AppException):
    """Rate limit exceeded."""
    def __init__(self, detail: str = "Demasiadas solicitudes. Intenta más tarde."):
        super().__init__(detail=detail, status_code=status.HTTP_429_TOO_MANY_REQUESTS)


class SessionExpiredError(AppException):
    """Session expired."""
    def __init__(self, detail: str = "Sesión expirada por inactividad"):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)
