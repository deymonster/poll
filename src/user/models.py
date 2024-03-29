from sqlalchemy import Boolean, Column, Integer, String, ARRAY
from sqlalchemy.orm import relationship
import uuid
from db.base_class import Base
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum


class UserRole(str, Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    USER = "user"


class User(Base):
    """ Model User """
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)
    _roles = Column("roles", String, default=UserRole.USER.value)

    @property
    def roles(self):
        return self._roles.split(",")

    @roles.setter
    def roles(self, roles):
        self._roles = ",".join(roles)

    poll = relationship("Poll", back_populates="user")
    response = relationship("Response", back_populates="user")


# class UserUUID(Base):
#     """ Model User with UUID"""
#     id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
#     # id = Column(Integer, primary_key=True, index=True)
#     full_name = Column(String, index=True)
#     email = Column(String, unique=True, index=True)
#     hashed_password = Column(String)
#     verified = Column(Boolean(), nullable=False, server_default=False)
#     is_active = Column(Boolean(), default=True)
#     is_superuser = Column(Boolean(), default=False)
#     poll = relationship("Poll", back_populates="user")
#     response = relationship("Response", back_populates="user")