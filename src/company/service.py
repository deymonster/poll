from base import schemas
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract
from collections import Counter
from company import schemas
from company import models as company_models
from fastapi import HTTPException
from user import models
from user.models import User
from company.models import Invitations


# TODO оформить все эти функции в метода класса Company с наследованием от базового класса Base!!!


# get all companies
def get_all_companies(db: Session):
    """
    Получить все компании

    :param db:
    :return: all companies
    """
    return db.query(models.Company).all()

def get_monthly_company(db: Session, year: int):
    """Получение статистики по месяцам компаний

    :param db: Сессия базы данных
    :param year: Год
    :return: количество компаний по месяцам
    """
    companies = db.query(
        extract('month', models.Company.created_at).label('month'),
    ).filter(
        extract('year', models.Company.created_at) == year
    ).all()

    # Подсчитываем количество компаний по месяцам
    monthly_counts = Counter(month for month, in companies)

    # Инициализируем список нулями для каждого месяца
    monthly_registrations = [monthly_counts[i] for i in range(1, 13)]

    # Общее количество компаний за год - это просто длина списка companies
    total_count = len(companies)

    return {
        "monthly_registrations": monthly_registrations,
        "total_count": total_count
    }

# create new company
def create_new_company(db: Session, data: schemas.CompanyCreate):
    """
    Создать новую компанию

    :param db:
    :param data:
    :return: new company
    """
    # TODO добавить проверку компании по ИНН если она уже есть то ошибку return
    new_company = models.Company(**data.model_dump())
    db.add(new_company)
    db.commit()
    db.refresh(new_company)
    return new_company.id


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


def get_company_by_inn(db: Session, inn: str):
    """ Получение компании по ИНН
    :param  db: Session
    :param inn: INN company
    :return company
    """
    db_company = db.query(models.Company).filter_by(inn=inn).first()
    if db_company:
        return db_company


# update company by id
def update_company_by_id(db: Session, company_id: int, data: schemas.CompanyUpdate):
    """
    Обновить компанию по id

    :param db: Session
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


def update_company_status(db: Session, company_id: int, payload_status: schemas.CompanyStatusUpdate):
    """
    Обновление статуса компании и всех ее пользователей
    :param db: Session
    :param company_id:  Company ID
    :param payload_status: Status - True or False
    """
    db_company = db.query(models.Company).filter_by(id=company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")
    db_company.subscription_active = payload_status.company_status
    users = db.query(User).filter(User.company_id == company_id).all()

    for user in users:
        user.is_active = payload_status.company_status
    db.commit()
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


def delete_invitation(db: Session, email: str):
    """
    Удалаяем приглашение по email
    :param db: Session
    :param email: user email
    :return db_invitation
    """
    db_invitation = db.query(company_models.Invitations).filter_by(email=email).first()
    if not db_invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    db.delete(db_invitation)
    db.commit()
    return db_invitation


def change_invitation_status(db: Session, email: str):
    """
    Меняем статус приглашения на неактивный
    :param db: Session
    :param email: User email
    :return:
    """
    db_invitation = db.query(company_models.Invitations).filter_by(email=email).first()
    if not db_invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    db_invitation.is_active = False
    db.commit()
    return db_invitation


def get_invitation_by_token(db: Session, token: str) -> Invitations:
    """ Получаем активное приглашение по токена
    :param db: Session
    :param token: Toke
    :return Invitation model
    """
    return db.query(company_models.Invitations).filter(company_models.Invitations.token == token).first()
