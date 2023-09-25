from db.base_class import Base
from enum import Enum
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime


class Company(Base):
    """Model company"""

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, comment="Наименование")
    full_name = Column(String, index=True, comment="Полное наименование")
    inn = Column(String, index=True, comment="ИНН")
    legal_address = Column(String, comment="Юридический адрес")
    actual_address = Column(String, comment="Фактический адрес")
    phone = Column(String, comment="Телефон")
    director_name = Column(String, comment="Ф.И.О руководителя")
    admin_email = Column(String, unique=True, index=True, comment="Почта для регистрации админа")
    licenses = Column(Integer, default=0, comment="Количество лицензий")
    users = relationship("User", back_populates="company")
    subscription_start = Column(DateTime, nullable=True, comment="Дата начала подписки")
    subscription_end = Column(DateTime, nullable=True, comment="Дата окончания подписки")
    subscription_active = Column(Boolean, default=True, comment="Статус подписки")
