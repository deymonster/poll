# exceptions.py

class TokenError(Exception):
    """Базовое исключение для ошибок токена."""
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details


class TokenExpiredError(TokenError):
    """Исключение для истекшего токена."""
    pass


class CustomInvalidTokenError(TokenError):
    """Исключение для недействительного токена."""
    pass
