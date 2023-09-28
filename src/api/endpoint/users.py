from typing import List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Body, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import EmailStr

from sqlalchemy.orm import Session
from fastapi import Request
from starlette.responses import JSONResponse

from base.schemas import Msg
from core import config
from core.security import get_password_hash
from utils import send_new_account_email, generate_registration_token, verify_registration_token, \
    send_new_account_complete_registration_email
from api.utils.db import get_db
from api.utils.security import get_current_active_user, get_current_user_with_roles, get_current_user

from user.models import User as DBUser, UserRole
from user.schemas import User, UserCreate, UserUpdate, TokenData, RegistrationCompletion, UserCreateByEmail
from user.service import crud_user
from fastapi import BackgroundTasks
from api.utils.logger import PollLogger

# Logging
logger = PollLogger(__name__).get_logger()

router = APIRouter()


@router.get("", response_model=List[User])
def read_users(
        db: Session = Depends(get_db),
        skip: int = 0,
        limit: int = 100,
        current_user: User = Depends(get_current_active_user)):
    """
    Получение списка пользователей

    :param db: Сессия базы данных
    :param skip: Количество пропускаемых записей
    :param limit: Количество возвращаемых записей
    :param current_user: Текущий пользователь с ролью суперпользователя
    :return: Список пользователей
    """
    # Проверяем роли - допускаются только SUPERADMIN и ADMIN
    get_current_user_with_roles(current_user, required_roles=[UserRole.SUPERADMIN, UserRole.ADMIN])
    # Передаем текущего пользователя с ролью в метод get_multi
    users = crud_user.get_multi(db, current_user=current_user, skip=skip, limit=limit)
    return users


# endpoint for pre-registration user
@router.post("/register", response_model=Msg)
def pre_register_user(
        *,
        request: Request,
        db: Session = Depends(get_db),
        user_in: UserCreateByEmail,
        background_tasks: BackgroundTasks,
        current_user: User = Depends(get_current_active_user)
):
    """
    Эндпойнт для регистрации пользователя.

    :param request Request from client
    :param db: Сессия базы данных
    :param user_in: Данные для создания пользователя
    :param background_tasks: BackgroundTasks
    :param current_user: Текущий пользователь с любой ролью
    :return: Сообщение об успешной предварительной регистрации

    Пример схемы для регистрации пользователя
    {
    "email": "popov@nitshop.ru",
    "full_name": "Попов Дмитрий",
    "roles": ["ADMIN", "USER"]
    }
    """
    # restrict access for superadmin and admin
    get_current_user_with_roles(current_user, required_roles=[UserRole.SUPERADMIN, UserRole.ADMIN])

    try:
        crud_user.register_user(db_session=db,
                                request=request,
                                current_user=current_user,
                                obj_in=user_in,
                                background_tasks=background_tasks)
        return JSONResponse(status_code=201, content={"message": "Email was sent to user"})
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"message": e.detail})


# endpoint for verification registration token
@router.post("/register/verify", response_model=Msg)
def verify_token(token_data: TokenData):
    """ Эндпойнт для проверки токена регистрации

    :param token_data: Схема для проверки токена регистрации
    :return возвращает сообщение о валидности токена
    Пример тела запроса:
    {
    "token": "{token}"
    }
    """
    result = verify_registration_token(token_data.token)
    if isinstance(result, ValueError):
        raise HTTPException(status_code=400, detail=str(result))
    return {"msg": "Token is valid"}


# endpoint for complete registration with token and password
@router.post("/register/complete")
def complete_registration(data: RegistrationCompletion,
                          background_tasks: BackgroundTasks,
                          db: Session = Depends(get_db),
                          ):
    """
    Эндпойнт для завершения регистрации пользователя.

    :param data: Схема для завершения регистрации пользователя
    :param background_tasks: BackgroundTasks
    :param db: Сессия базы данных
    :return: Сообщение об успешном завершении регистрации

    1. Проверяем токен регистрации, при успешной проверке получаем из него email и роли
    2. Проверяем наличие пользователя с таким же email в БД
    2. Хэшируем новый пароль
    3. Создаем нового пользователя с привязкой к компании
    4. Отправляем письмо об успешной регистрации
    5. Возвращаем 201 код и сообщение об успешном создании пользователя

    Пример схемы для завершения регистрации пользователя
    {
    "token": "{token}"
    "password": "{password}"
    "company_id": "1"
    "full_name": "Петрова Анна Юрьевна"
    }
    """
    email, roles = verify_registration_token(data.token)
    if crud_user.get_by_email(db, email=email):
        raise HTTPException(
            status_code=409,
            detail="The user with this username already exists in the system.",
        )
    if not email or not roles:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    # hash new password
    hashed_password = get_password_hash(data.password)
    # create new user
    user_in = DBUser(full_name=data.full_name,
                     email=email,
                     hashed_password=hashed_password,
                     is_active=True,
                     roles=roles,
                     company_id=data.company_id)
    db.add(user_in)
    db.commit()
    # send email about successful registration in background
    background_tasks.add_task(send_new_account_complete_registration_email,
                              email_to=user_in.email,
                              email=user_in.email,
                              full_name=user_in.full_name)
    return JSONResponse(status_code=201, content={"message": "User created successfully"})


@router.post("", response_model=User, status_code=201, deprecated=True)
def create_user(
        *,
        db: Session = Depends(get_db),
        user_in: UserCreate,
        current_user: User = Depends(lambda: get_current_user_with_roles([UserRole.SUPERADMIN, UserRole.ADMIN])),
):
    """
    Простой эндпойнт для создания пользователя.
    :param db: Сессия базы данных
    :param user_in: Данные для создания пользователя
    :param current_user: Текущий пользователь с ролью SUPERADMIN и ADMIN
    :return: Созданный пользователь

    1. Проверяем, существует ли пользователь с таким же email
    2. Если пользователь существует, то возвращаем ошибку
    3. Если пользователь не существует, то создаем его
    4. Если включена отправка email, то отправляем письмо с данными для входа в систему
    """
    user = crud_user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=409,
            detail="The user with this username already exists in the system.",
        )
    user = crud_user.create(db, obj_in=user_in)
    if config.EMAILS_ENABLED and user_in.email:
        send_new_account_email(email_to=user_in.email, email=user_in.email, password=user_in.password)
    return JSONResponse(status_code=201, content={"message": "User created successfully"})


@router.put("/{user_id}", response_model=User)
@router.put("/me", response_model=User)
def update_user_me(
        user_id: Optional[int] = None,
        *,
        db: Session = Depends(get_db),
        user_in: UserUpdate,
        current_user: DBUser = Depends(get_current_active_user),
):
    """
    Эндпойнты для обновления конкретного пользователя по id  и второй для обновления текущего пользователя.

    :param user_id: ID пользователя - необязательный параметр для обновления пользователя по id
    :param db: Сессия базы данных
    :param user_in: Данные для обновления пользователя
    :param current_user: Текущий пользователь со статусом активный
    :return: Обновленный пользователь

    Схема для обновления данных
    {
    "email": "{email}",
    "is_active": True,
    "full_name": "{Some full name}",
    "roles": [UserRole.USER, UserRole.ADMIN],
    "password": "0000"
    }
    """
    if not user_id:
        user_id = current_user.id
    user_to_update = crud_user.get_or_404(db, user_id=user_id, current_user=current_user)
    try:
        crud_user.update(db, current_user=current_user, db_obj=user_to_update, update_data=user_in)
        return JSONResponse(status_code=201, content={"message": "User updated successfully"})
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"message": e.detail})



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


@router.get("/{user_id}", response_model=User)
def read_user_by_id(user_id: int,
                    current_user: User = Depends(get_current_active_user),
                    db: Session = Depends(get_db)):
    """
    Эндпойнт для получения пользователя по user_id
    :param user_id пользователя
    :param current_user Текущий пользователь со статусом активный
    :param db Сессия базы данных
    :return возвращаем текущего пользователя

    1. Проверяем роль пользователя  - только админ и суперадмин
    2. Получаем пользователя по id
    """
    get_current_user_with_roles(current_user, required_roles=[UserRole.SUPERADMIN, UserRole.ADMIN])
    user = crud_user.get_or_404(db, user_id=user_id, current_user=current_user)
    return user


# @router.put("/{user_id}", response_model=User)
# def update_user(*, db: Session = Depends(get_db), user_id: int, user_in: UserUpdate,
#                 current_user: DBUser = Depends(get_current_active_user),
#                 ):
#     """
#     Эндпойнт для обновления данных пользователя
#     :param db Сессия базы данных
#     :param user_id ID пользователя
#     :param user_in Схема для обновления пользователя
#     :param current_user текущий пользователя с правами суперадмин
#     :return возвращаем обновленного пользователя
#     """
#     crud_user.update(db, current_user=current_user, db_obj=current_user, update_data=user_in)
#     return JSONResponse(status_code=201, content={"message": "User updated successfully"})


# endpoint for deleting user
@router.delete("/{user_id}", response_model=Msg)
def delete_user(*, db: Session = Depends(get_db), user_id: int,
                current_user: User = Depends(get_current_active_user),
                ):
    """Эндпойнт для удаления пользователя
    :param db Сессия базы данных
    :param user_id ID пользователя
    :param current_user текущий пользователя с правами суперадмин
    :return Msg - message about deleting"""
    get_current_user_with_roles(current_user, required_roles=[UserRole.SUPERADMIN, UserRole.ADMIN])
    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system",
        )
    try:
        crud_user.remove(db_session=db, id=user_id)
        return {"msg": "User was deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error while deleting user {e}")
