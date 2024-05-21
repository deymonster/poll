from typing import List, Optional

from pydantic import Field
from pydantic.main import BaseModel

from utils import CamelModelMixin
from dataclasses import dataclass
from datetime import timedelta, datetime


@dataclass
class TokenData:
    """Dataclass for token data"""

    user_id: str

    def to_dict(self):
        return {
            "user_id": self.user_id,
        }


@dataclass
class TokenPayload:
    """Dataclass for token payload"""

    user_id: int
    exp: int
    sub: str


@dataclass
class AnonymTokenPayload:
    """Dataclass for poll token to identify users """

    poll_uuid: str
    sub: str
    timestamp: datetime


class RefreshToken(CamelModelMixin):
    refresh_token: str = Field(..., description="Токен обновления")


class Message(CamelModelMixin):
    message: str


class AvatarUpload(Message):
    path_to_avatar:  Optional[str] = None




class TokenVerificationResponse(CamelModelMixin):
    message: str
    email: str
    roles: List[str]
    full_name: str
    company_id: Optional[int] = None
