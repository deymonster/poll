from typing import Optional, List
from pydantic import BaseModel, EmailStr
import uuid
from enum import Enum


class Roles(str, Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    USER = "user"


class UserBase(BaseModel):
    email: EmailStr
    is_active: Optional[bool] = False
    full_name: Optional[str] = None
    roles: List[str] = []

    class Config:
        orm_mode = True


class UserBaseInDB(UserBase):
    id: Optional[int] = None


class UserCreate(UserBase):
    pass


class UserCreateByEmail(UserBase):
    email: str


class UserUpdate(UserBase):
    password: Optional[str] = None


class User(UserBaseInDB):
    pass


class UserInDB(UserBaseInDB):
    hashed_password: str


class TokenData(BaseModel):
    token: str


class RegistrationCompletion(BaseModel):
    token: str
    password: str
    company_id: int
    full_name: Optional[str] = None


