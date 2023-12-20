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


class InactiveInvitationError(TokenError):
    """Исключение для неактивного приглашения"""
    pass


class NoInvitiationError(TokenError):
    """ Исключение для отсуствуещего приглашеия"""
    pass