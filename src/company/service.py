from base import schemas
from sqlalchemy.orm import Session, joinedload
from company import schemas
from company import models
from fastapi import HTTPException


# get all companies
def get_all_companies(db: Session):
    """Get all companies"""
    return db.query(models.Company).all()


# create new company
def create_new_company(db: Session, data: schemas.CompanyCreate):
    """Create new company"""
    new_company = models.Company(**data.dict())
    db.add(new_company)
    db.commit()
    db.refresh(new_company)
    return new_company


# get company by id
def get_company_by_id(db: Session, company_id: int):
    """Get company by id"""
    return db.query(models.Company).filter_by(id=company_id).first()


# update company by id
def update_company_by_id(db: Session, company_id: int, data: schemas.CompanyUpdate):
    """Update company by id"""
    db_company = db.query(models.Company).filter_by(id=company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")
    for field, value in data.dict(exclude_unset=True).items():
        setattr(db_company, field, value)
    db.commit()
    db.refresh(db_company)
    return db_company


# delete company by id
def delete_company_by_id(db: Session, company_id: int):
    """Delete company by id"""
    db_company = db.query(models.Company).filter_by(id=company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")
    db.delete(db_company)
    db.commit()
    return db_company
