from pydantic import BaseModel, Field, constr, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime


class CompanyBaseId(BaseModel):
    id: int


class CompanyCreate(BaseModel):
    """Base model schemas for creating company"""
    name: str
    full_name: str
    inn: constr(pattern=r'^\d{10,12}$')  # TODO add validation INN later
    legal_address: str
    actual_address: str
    phone: str
    director_name: str
    admin_email: constr(pattern=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
    licenses: int = 0
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    subscription_active: Optional[bool] = True

    # @validator('inn')
    # def validate_inn(self, inn):
    #     # ADD VALIDATION INN HERE
    #     return inn

    class Config:
        orm_mode = True


class CompanyOut(CompanyBaseId, CompanyCreate):
    """Base model schemas for company"""
    pass


class CompanyUpdate(BaseModel):
    """Schema for updating a company"""
    name: Optional[str] = None
    full_name: Optional[str] = None
    inn: Optional[constr(pattern=r'^\d{10,12}$')] = None
    legal_address: Optional[str] = None
    actual_address: Optional[str] = None
    phone: Optional[str] = None
    director_name: Optional[str] = None
    admin_email: Optional[constr(pattern=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')] = None
    licenses: Optional[int] = None
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    subscription_active: Optional[bool] = None





