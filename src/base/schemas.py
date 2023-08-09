from typing import List

from pydantic import Field
from pydantic.main import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    user_id: int = None
    exp: int
    roles: List[str]


class RefreshTokenPayload(BaseModel):
    user_id: int = None
    exp: int


class RefreshToken(BaseModel):
    refresh_token: str = Field(..., description="Токен обновления")


class Msg(BaseModel):
    msg: str



