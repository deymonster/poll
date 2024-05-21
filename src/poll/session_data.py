from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID


@dataclass
class SessionData:
    """
    Датакласс для хранения сессии в Mongo.

    Параметры
    _____

    token:
        Токен с UUID и текущим временем
    fingerprint:
        Уникальный пользовательский отпечаток из fingerprintJS
    poll_uuid:
        UUID опроса
    expires_at: (по умолчанию None)
        Datetime поле - время когда сессия станет недействительной
    expired: (по умолчанию False)
        Bool - статус указывающий что сессия истекла
    answered: (по умолчанию False)
        Bool - статус указывающий что пользователь дал ответ на опрос

    """
    token: str
    poll_uuid: UUID
    fingerprint: str = field(default='')
    expires_at: Optional[datetime] = field(default=None)
    expired: bool = field(default=False)
    answered: bool = field(default=False)
    session_status: str = field(default='')

    def __post_init__(self):
        self.poll_uuid = str(self.poll_uuid)

    def to_dict(self):
        return asdict(self)

