from base import schemas
from sqlalchemy.orm import Session, joinedload
from company import schemas
from company import models as company_models
from fastapi import HTTPException
from user import models

# TODO оформить все эти функции в метода класса Company с наследованием от базового класса Base!!!


# get all companies
def get_all_companies(db: Session):
    """
    Получить все компании

    :param db:
    :return: all companies
    """
    return db.query(models.Company).all()


# create new company
def create_new_company(db: Session, data: schemas.CompanyCreate):
    """
    Создать новую компанию

    :param db:
    :param data:
    :return: new company
    """
    new_company = models.Company(**data.dict())
    db.add(new_company)
    db.commit()
    db.refresh(new_company)
    return new_company


# get company by id
def get_company_by_id(db: Session, company_id: int):
    """
    Получение компании по id

    :param db:
    :param company_id:
    :return: company
    """
    db_company = db.query(models.Company).filter_by(id=company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")
    return db_company


# update company by id
def update_company_by_id(db: Session, company_id: int, data: schemas.CompanyUpdate):
    """
    Обновить компанию по id

    :param db:
    :param company_id:
    :param data: схема CompanyUpdate
    :return: updated company
    """
    db_company = get_company_by_id(db, company_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(db_company, field, value)
    db.commit()
    db.refresh(db_company)
    return db_company


# delete company by id
def delete_company_by_id(db: Session, company_id: int):
    """
    Удалить компанию по id

    :param db: Session
    :param company_id: int
    :return: Company
    """
    db_company = get_company_by_id(db, company_id)
    db.delete(db_company)
    db.commit()
    return db_company


# count registered users
def count_registered_users(db: Session, company_id: int):
    """
    Подсчет зарегистрированных пользователей в компании

    :param db: Session
    :param company_id: int
    :return: int
    """
    return db.query(models.User).filter(models.User.company_id == company_id).count()


# count active invitations
def count_active_invitations(db: Session, company_id: int):
    """
    Подсчет активных приглашений в компании

    :param db: Session
    :param company_id: int
    :return: int
    """
    return db.query(company_models.Invitations).filter(company_models.Invitations.company_id == company_id).count()


# ability to invite new users
def can_invite_new_users(db: Session, company_id: int) -> bool:
    """
    Возможность приглашать новых пользователей

    :param db: Session
    :param company_id: int
    :return: bool
    """
    db_company = get_company_by_id(db, company_id)
    total_users = count_registered_users(db, company_id)
    total_invitations = count_active_invitations(db, company_id)
    return (total_users + total_invitations) < db_company.licenses


# add record to invitations table
def add_invitation(db: Session, company_id: int, email: str, token: str):
    """
    Добавляет запись в таблицу приглашений

    :param db: Session
    :param company_id: int
    :param email: str
    :param token: str
    :return: Invitations model
    """
    db_invitation = company_models.Invitations(
        company_id=company_id,
        email=email,
        token=token
    )
    db.add(db_invitation)
    db.commit()
    db.refresh(db_invitation)
    return db_invitation

