from typing import List

from pydantic import Field
from pydantic.main import BaseModel

from utils import CamelModelMixin
from dataclasses import dataclass
from datetime import timedelta


@dataclass
class TokenData:
    """ Dataclass for token data """

    user_id: str

    def to_dict(self):
        return {
            "user_id": self.user_id,
        }


@dataclass
class TokenPayload:
    """ Dataclass for token payload """

    user_id: int
    exp: int
    sub: str


class RefreshToken(CamelModelMixin):
    refresh_token: str = Field(..., description="Токен обновления")


class Message(CamelModelMixin):
    msg: str



