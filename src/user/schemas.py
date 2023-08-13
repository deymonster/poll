from typing import Optional, List
from pydantic import BaseModel, constr
import uuid


class UserBase(BaseModel):
    email: Optional[str] = None
    is_active: Optional[bool] = False
    full_name: Optional[str] = None
    roles: Optional[List[str]] = []

    class Config:
        orm_mode = True


class UserBaseInDB(UserBase):
    id: Optional[int] = None


class UserCreate(UserBase):
    email: str
    password: str


class UserCreateByEmail(UserBase):
    email: str


class UserUpdate(UserBase):
    password: Optional[str] = None


class User(UserBaseInDB):
    pass


class UserInDB(UserBaseInDB):
    hashed_password: str

