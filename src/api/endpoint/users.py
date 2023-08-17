from typing import List

from fastapi import APIRouter, Depends, Body, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import EmailStr

from sqlalchemy.orm import Session

from core import config
from utils import send_new_account_email
from api.utils.db import get_db
from api.utils.security import get_current_active_user, get_current_user_with_role, get_current_user

from user.models import User as DBUser, UserRole
from user.schemas import User, UserCreate, UserUpdate
from user.service import crud_user

router = APIRouter()


@router.get("", response_model=List[User])
def read_users(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(lambda: get_current_user_with_role(UserRole.SUPERADMIN)),
):
    """
    Получение списка пользователей
    :param db: Сессия базы данных
    :param skip: Количество пропускаемых записей
    :param limit: Количество возвращаемых записей
    :param current_user: Текущий пользователь с ролью суперпользователя
    """
    users = crud_user.get_multi(db, skip=skip, limit=limit)
    return users


@router.post("", response_model=User)
def create_user(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
    current_user: User = Depends(lambda: get_current_user_with_role(UserRole.SUPERADMIN)),
):
    """
    Простой эндпойнт для создания пользователя.
    :param db: Сессия базы данных
    :param user_in: Данные для создания пользователя
    :param current_user: Текущий пользователь с ролью суперпользователя
    :return: Созданный пользователь

    1. Проверяем, существует ли пользователь с таким же email
    2. Если пользователь существует, то возвращаем ошибку
    3. Если пользователь не существует, то создаем его
    4. Если включена отправка email, то отправляем письмо с данными для входа в систему
    """
    user = crud_user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    user = crud_user.create(db, obj_in=user_in)
    if config.EMAILS_ENABLED and user_in.email:
        send_new_account_email(email_to=user_in.email, email=user_in.email, password=user_in.password)
    return user


@router.put("/me", response_model=User)
def update_user_me(
    *,
    db: Session = Depends(get_db),
    password: str = Body(None),
    full_name: str = Body(None),
    email: EmailStr = Body(None),
    current_user: DBUser = Depends(get_current_active_user),
):
    """
    Эндпойнт для обновления данных текущего пользователя.

    :param db: Сессия базы данных
    :param password: Новый пароль
    :param full_name: Новое полное имя
    :param email: Новый email
    :param current_user: Текущий пользователь со статусом активный
    :return: Обновленный пользователь

    1. Получаем данные текущего пользователя в виде словаря
    2. Создаем объект для обновления данных пользователя
    3. Делаем проверку данных для изменения, если данные не None то меняем объект для обновления пользователя
    4. Вызывыаем метод update из экземпляра класса crud_user

    """
    current_user_data = jsonable_encoder(current_user)
    user_in = UserUpdate(**current_user_data)
    if password is not None:
        user_in.password = password
    if full_name is not None:
        user_in.full_name = full_name
    if email is not None:
        user_in.email = email
    user = crud_user.update(db, db_obj=current_user, obj_in=user_in)
    return user


@router.get("/me", response_model=User)
def read_user_me(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user),
):
    """
    Эндпойнт для получения данных текущего активного пользователя
    :param db Сессия базы данных
    :param current_user Текущий пользователь со статусом активный

    :return возвращаем текущего пользователя
    """
    return current_user


@router.post("/open", response_model=User, deprecated=True)
def create_user_open(
    *,
    db: Session = Depends(get_db),
    password: str = Body(...),
    email: EmailStr = Body(...),
    full_name: str = Body(None),
):
    """
    Create new user without the need to be logged in.
    """
    if not config.USERS_OPEN_REGISTRATION:
        raise HTTPException(
            status_code=403,
            detail="Open user registration is forbidden on this server",
        )
    user = crud_user.get_by_email(db, email=email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system",
        )
    user_in = UserCreate(password=password, email=email, full_name=full_name)
    user = crud_user.create(db, obj_in=user_in)
    return user


@router.get("/{user_id}", response_model=User)
def read_user_by_id(user_id: int, current_user: DBUser = Depends(get_current_active_user),
                    db: Session = Depends(get_db)):
    """
    Эндпойнт для получения пользователя по user_id
    :param user_id пользователя
    :param current_user Текущий пользователь со статусом активный
    :param db Сессия базы данных
    :return возвращаем текущего пользователя

    1. Получаем пользователя по id полученному из параметра запроса
    2. Проводим проверку, если полученный пользователя является текущим активным пользователем \
        возвращаем его, инача ошибка 400
    """
    user = crud_user.get(db, id=user_id)
    if user == current_user:
        return user
    if not crud_user.is_superuser(current_user):
        raise HTTPException(status_code=400, detail="The user doesn't have enough privileges")
    return user


@router.put("/{user_id}", response_model=User)
def update_user(*, db: Session = Depends(get_db), user_id: int, user_in: UserUpdate,
                current_user: User = Depends(lambda: get_current_user_with_role(UserRole.SUPERADMIN)),
):
    """
    Эндпойнт для обновления данных пользователя
    :param db Сессия базы данных
    :param user_id ID пользователя
    :param user_in Схема для обновления пользователя
    :param current_user текущий пользователя с правами суперадмин
    :return возвращаем обновленного пользователя
    """
    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system",
        )
    user = crud_user.update(db, db_obj=user, obj_in=user_in)
    return user
