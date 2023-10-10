from typing import Optional, List
from pydantic import BaseModel, EmailStr
import uuid
from enum import Enum


class Roles(str, Enum):
    """
    User roles
    """
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    USER = "user"


class UserBase(BaseModel):
    """
    Base user model
    """
    email: EmailStr
    is_active: Optional[bool] = False
    full_name: Optional[str] = None
    roles: List[str] = []

    class Config:
        orm_mode = True


class UserBaseInDB(UserBase):
    """
    Base user model in DB
    """
    id: Optional[int] = None


class UserCreate(UserBase):
    """
    User create model
    """
    password: str


class UserCreateByEmail(UserBase):
    """
    User create model by email
    """
    email: str


class UserUpdate(UserBase):
    """
    User update model
    """
    password: Optional[str] = None


class User(UserBaseInDB):
    """
    User model
    """
    pass


class UserInDB(UserBaseInDB):
    """
    User model in DB
    """
    hashed_password: str


class TokenData(BaseModel):
    """
    Token data model
    """
    token: str


class RegistrationCompletion(BaseModel):
    """
    Registration completion model
    """
    token: str
    password: str
    company_id: int
    full_name: Optional[str] = None


