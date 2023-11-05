from typing import List

from pydantic import Field
from pydantic.main import BaseModel

from utils import CamelModelMixin


class Token(CamelModelMixin):
    access_token: str
    token_type: str


class TokenPayload(CamelModelMixin):
    user_id: int = None
    exp: int
    roles: List[str]


class RefreshTokenPayload(CamelModelMixin):
    user_id: int = None
    exp: int


class RefreshToken(CamelModelMixin):
    refresh_token: str = Field(..., description="Токен обновления")


class Msg(CamelModelMixin):
    msg: str



