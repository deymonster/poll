
from datetime import timedelta
from fastapi import Request
import jwt
from jwt import PyJWTError
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from starlette import status

from core import config
from core.jwt import create_access_token, create_refresh_token, ALGORITHM
from core.security import get_password_hash

from api.utils.db import get_db
from api.utils.security import get_current_user
from base.schemas import Msg, Token, TokenPayload, RefreshToken, RefreshTokenPayload
from user.models import User as DBUser
from user.schemas import User, UserCreate, UserCreateByEmail
from user.service import crud_user
from utils import (generate_password_reset_token,
                   send_reset_password_email, verify_password_reset_token)
from starlette.responses import Response, RedirectResponse, JSONResponse
from urllib.parse import urlparse
from fastapi import BackgroundTasks
from api.utils.logger import PollLogger

# Logging
logger = PollLogger(__name__).get_logger()

router = APIRouter()


# endpoint to login with  vue js
@router.post("/login", summary="Авторизация", description="Авторизация пользователя в системе")
def login_access_token_vue(
        response: Response, db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    """ Эндпоинт для авторизации пользователя в системе.

    :param response: Ответ сервера для установки куки
    :param db: Сессия базы данных
    :param form_data: Зависимость от класса OAuth2PasswordRequestForm для получения данных из формы
    :return: Возвращает сообщение об успешной авторизации,  токен доступа и токен обновления
    Тип данных x-www-form-urlencoded
    1. Проверяем существует ли пользователь с таким email
    2. Проверяем активен ли пользователь
    3. Генерируем токен доступа с учетом ролей пользователя и устанавливаем время жизни токена
    4. Генерируем токен обновления и устанавливаем время жизни токена
    5. Возвращаем сообщение об успешной авторизации,  токен доступа и токен обновления
    """
    user = crud_user.authenticate(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not crud_user.is_active(user):
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "roles": user.roles}, user_id=user.id, expire_delta=access_token_expires
    )

    refresh_token_expires = timedelta(minutes=config.REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = create_refresh_token(data={"sub": user.email}, user_id=user.id, expire_delta=refresh_token_expires)

    return {
        "message": "Login successfull",
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


# endpoint for refresh token for vue js
@router.post("/refresh", summary="Обновление токена", description="Обновление токена доступа")
def login_refresh_token_vue(token_data: RefreshToken, db: Session = Depends(get_db)):
    """ " Эндпоинт для обновления токена доступа.
    :param token_data: Зависимость от класса RefreshToken для получения данных из тела запроса
    :param db: Сессия базы данных
    :return: Возвращает токен доступа и токен обновления

    1. Проверяем токен обновления на валидность с использованием секретного ключа
    2. Извлекаем индефикатор пользователя из токена обновления и врея жизни токена
    3. Проверяем наличие пользователя в базе данных и его активный статус
    4. Генерируем новый токен доступа и токен обновления
    5. Возвращаем токен доступа и токен обновления в JSON формате

    Пример запроса:
    POST /api/refresh
    Content-Type: application/json
    {
        "refresh_token": "your refresh token"
    }
    Пример ответа:
    {
        "access_token": "your access token"
    }
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        refresh_token = token_data.refresh_token
        payload = jwt.decode(refresh_token, config.SECRET_KEY, algorithms=[ALGORITHM])
        print(f"Token payload: {payload}")
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        token_data = RefreshTokenPayload(user_id=user_id, exp=payload.get("exp"))
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, jwt.ImmatureSignatureError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired or invalid")
    except PyJWTError:
        raise credentials_exception
    user = crud_user.get(db, id=token_data.user_id)
    if user is None or not crud_user.is_active(user):
        raise credentials_exception

    access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, user_id=user.id, expire_delta=access_token_expires
    )
    return {"access_token": access_token}


@router.post("/test_access_token", response_model=User, deprecated=True)
def test_token(current_user: DBUser = Depends(get_current_user)):
    """
    Test access token
    """
    return current_user


@router.post("/password-recovery/{email}", response_model=Msg)
def recover_password(request: Request,backgroud_tasks: BackgroundTasks, email: str, db: Session = Depends(get_db)):

    """
    Эндпойнт для сброса пароля
    :param request Объект Request.
    :param backgroud_tasks: Зависимость от класса BackgroundTasks для отправки письма в фоновом режиме
    :param email: адрес электронной почты
    :param db:  Сессия базы данных
    :return Возвращает сообщение об отправленном сообщении на почту

    1. Проверяем наличие пользователя в базе данных по адресу электронной почты
    2. Генерируем токен сброса пароля
    3. Получаем адрес фронта из headers запроса - referer
    3. Отправляем письмо на почту пользователя с ссылкой для сброса пароля
    """
    user = crud_user.get_by_email(db, email=email)
    logger.info(f"User  get by email {user}")
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system.",
        )
    referer = request.headers.get("Referer")
    # TODO: add checking for empty referer etc
    frontend_url = f"{urlparse(referer).scheme}://{urlparse(referer).netloc}"
    password_reset_token = generate_password_reset_token(email=email)
    logger.info(f"Reset token {password_reset_token}")
    backgroud_tasks.add_task(send_reset_password_email, email_to=user.email, email=email, token=password_reset_token, \
                             front_url=frontend_url)
    return {"msg": "Password recovery email sent"}


# endpoint for vefication reset token
@router.get("/reset-password/verify", response_model=Msg)
def reset_password_verify_token(token: str = Body(...), db: Session = Depends(get_db)):
    email = verify_password_reset_token(token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")
    # return resonse with code 200 and message about valid token
    return {"msg": "Token is valid"}


@router.post("/reset-password", response_model=Msg)
def reset_password(token: str = Body(...), new_password: str = Body(...), db: Session = Depends(get_db)):
    """
    Эндпойнт для сброса пароля по ссылке полученной из /password-recovery/{email}".
    :param token: токен сброса пароля
    :param new_password: новый пароль
    :param db: Сессия базы данных
    :return Возвращает сообщение об успешном сбросе пароля

    1. Получаем токен из тела запроса и далее из токена получаем адрес электронной почты
    2. Проверяем наличие пользователя в базе данных по адресу электронной почты
    3. Проверяем активность пользователя
    4. Хэшируем новый пароль
    5. Обновляем пароль пользователя в базе данных

    Ссылка приходит такого вида:
    http://127.0.0.1:4000/reset-password?token={token}
    TODO верификация временнного токена при восстановлении пароля по ссылке перед сменой пароля
    """
    email = verify_password_reset_token(token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")
    user = crud_user.get_by_email(db, email=email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    elif not crud_user.is_active(user):
        raise HTTPException(status_code=400, detail="Inactive user")
    hashed_password = get_password_hash(new_password)
    user.hashed_password = hashed_password
    db.commit()
    return {"msg": "Password updated successfully"}

# TODO сделать эндпойты для регистрации пользователей с отправкой ccылки для установки пароля полльвателем


