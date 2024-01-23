from typing import Optional, List

import jwt
from fastapi import Depends, HTTPException, Security, Request, Header
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import RedirectResponse
from starlette.status import (
    HTTP_403_FORBIDDEN,
    HTTP_302_FOUND,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR)

from core.security import get_password_hash
from db.session import SessionLocal
from poll import models
from user.schemas import UserCreate
from user.service import crud_user
from api.utils.db import get_db
from core import config
from core.jwt import ALGORITHM
from user.models import User, UserRole
from base.schemas import TokenPayload, AnonymTokenPayload
from datetime import datetime, timedelta
from core.jwt import create_access_token, create_refresh_token, ALGORITHM
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2
from fastapi.security.utils import get_authorization_scheme_param
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from api.utils.logger import PollLogger

# Logging
logger = PollLogger(__name__)


# reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/login/access-token")


class Oauth2PasswordBearerCookie(OAuth2):
    def __init__(
            self,
            tokenurl: str,
            scheme_name: str = None,
            scopes: dict = None,
            auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(password={"tokenUrl": tokenurl, "scopes": scopes})
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        authorization: str = request.cookies.get("Authorization")
        sheme, param = get_authorization_scheme_param(authorization)
        if not authorization or sheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        return param

# class HTTPCookieBearer(HTTPBearer):
#     def __init__(self, auto_error: bool = True):
#         super().__init__(auto_error=auto_error)
#
#     async def __call__(self, request: Request):
#         authorization: str = request.cookies.get("access_token")
#         scheme, param = get_authorization_scheme_param(authorization)
#         if not authorization or scheme.lower() != "bearer":
#             if self.auto_error:
#                 raise HTTPException(
#                     status_code=HTTP_403_FORBIDDEN, detail="Not authenticated"
#                 )
#             else:
#                 return None
#         return HTTPAuthorizationCredentials(scheme=scheme, credentials=param)


security = OAuth2PasswordBearer(tokenUrl="/api/login")


# create initial user
def create_initial_user(db: Session):
    """ Создание начального пользователя
    :param db: сессия БД
    :return: Возвращает созданного пользователя
    """
    user = crud_user.get_by_email(db, email="super@user.me")
    if not user:
        db_obj = UserCreate(
            email="super@user.me",
                password="qwe123QWE",
            full_name="Super Admin",
            is_active=True,
            roles=[UserRole.SUPERADMIN]
        )
        crud_user.create(db, obj_in=db_obj)


def get_current_user(token: str = Depends(security), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    """ Получение пользователя из токена
    :param token: токен
    :param db: сессия БД
    :return: Возвращает пользователя
    """
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithm=ALGORITHM)
        token_data = TokenPayload(**payload)
    except PyJWTError:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="Could not validate credentials"
        )
    user = crud_user.get(db, id=token_data.user_id)
    if not user:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")
    return user


def get_poll_session(token: str = Header(...), fingerprint: str = Header(None), db: Session = Depends(get_db)):
    """Получение информации о сессии пользователя который проходит опрос"""
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithm=ALGORITHM)
        token_data = AnonymTokenPayload(**payload)
        uuid = token_data.poll_uuid
    except PyJWTError:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="Could not validate credentials - no anonymous token"
        )
    user_session = db.query(models.UserSession).filter(models.Poll.uuid == uuid).first()
    if user_session is None:
        raise HTTPException(status_code=404, detail="Poll not found")
    if user_session.token:
        return user_session
    return None


def get_current_active_user(current_user: User = Security(get_current_user)):
    """ Получение активного пользователя

    :param current_user: текущий пользователь как зависимость get_current_user
    :return: Возвращает текущего пользователя если он активен
    """
    if not crud_user.is_active(current_user):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Get current user with role
def get_current_user_with_roles(current_user: User, required_roles: List[UserRole] = None):
    if not required_roles:
        return current_user
    if not any(role in current_user.roles for role in map(lambda r: r.value, required_roles)):
        raise HTTPException(status_code=403, detail="The user doesn't have enough privileges")
    return current_user


# # middleware for handling exceptions of HTTPCookieBearer
# async def auth_middleware(request: Request, call_next):
#     try:
#         return await call_next(request)
#     except HTTPException as e:
#         if e.status_code == HTTP_403_FORBIDDEN:
#             return RedirectResponse("//loginv3", status_code=status.HTTP_303_SEE_OTHER)
#         else:
#             response = e
#     except Exception as e:
#         return HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error - {str(e)}")


