from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Security, Request, Response, FastAPI
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import RedirectResponse
from starlette.status import HTTP_403_FORBIDDEN, HTTP_302_FOUND, HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND, \
    HTTP_500_INTERNAL_SERVER_ERROR

from core.security import get_password_hash
from db.session import SessionLocal
from user.schemas import UserCreate
from user.service import crud_user
from api.utils.db import get_db
from core import config
from core.jwt import ALGORITHM
from user.models import User, UserRole
from base.schemas import TokenPayload
from datetime import datetime, timedelta
from core.jwt import create_access_token, create_refresh_token, ALGORITHM
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2
from fastapi.security.utils import get_authorization_scheme_param
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel


# reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/login/access-token")

# UNPROTECTED_PATHS = [
#     "http://127.0.0.1:8000/login/access-token",
#     "http://127.0.0.1:8000/login/refresh-token",
#     "http://127.0.0.1:8000/login/test-token",
#     "http://127.0.0.1:8000/login",
#     "http://127.0.0.1:8000/loginv3",
#
# ]


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
    user = crud_user.get_by_email(db, email=config.FIRST_SUPERUSER)
    if not user:
        # user_in = User(
        #     email=config.FIRST_SUPERUSER,
        #     password=config.FIRST_SUPERUSER_PASSWORD,
        #     is_active=True,
        #     roles=[UserRole.SUPERADMIN],
        # )
        db_obj = UserCreate(
            email=config.FIRST_SUPERUSER,
            password=config.FIRST_SUPERUSER_PASSWORD,
            is_active=True,
            roles=[UserRole.SUPERADMIN]
        )
        user = crud_user.create(db, obj_in=db_obj)
    return user


def get_current_user(token: str = Depends(security), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        print(f"Token: {token}")
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=ALGORITHM)
        token_data = TokenPayload(**payload)
        print(f'token_data: {token_data.user_id}')
    except PyJWTError:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials"
        )
    user = crud_user.get(db, id=token_data.user_id)
    if not user:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")
    return user


def get_current_active_user(current_user: User = Security(get_current_user)):
    if not crud_user.is_active(current_user):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Get current user with role
def get_current_user_with_role(current_user: User = Depends(get_current_user), required_role: UserRole = None):
    if required_role and required_role not in current_user.roles:
        raise HTTPException(status_code=403, detail="The user doesn't have enough privileges")
    return current_user


# middleware for handling exceptions of HTTPCookieBearer
async def auth_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except HTTPException as e:
        if e.status_code == HTTP_403_FORBIDDEN:
            return RedirectResponse("//loginv3", status_code=status.HTTP_303_SEE_OTHER)
        else:
            response = e
    except Exception as e:
        return HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error - {str(e)}")


# async def access_token_middleware(request: Request, call_next):
#     try:
#         db = SessionLocal()
#         if str(request.url) not in UNPROTECTED_PATHS and not request.url.path.startswith("/static"):
#             access_token = request.cookies.get("access_token", None)
#             refresh_token = request.cookies.get("refresh_token", None)
#             if refresh_token is None:
#                 print(f'Refresh token is missing - {refresh_token}')
#                 response = Response(headers=request.headers)
#                 # remove cookies
#                 response.delete_cookie("access_token")
#                 response.delete_cookie("refresh_token")
#                 print(f'No refresh token - redirect to loginv3')
#                 return RedirectResponse("/loginv3", status_code=status.HTTP_303_SEE_OTHER)
#             else:
#                 if access_token is not None:
#                     access_token = access_token[7:] if access_token.lower().startswith("bearer") else access_token
#                     refresh_token = refresh_token[7:] if refresh_token.lower().startswith("bearer") else refresh_token
#             try:
#                 # try to decode access token
#                 payload = jwt.decode(access_token, config.SECRET_KEY, algorithms=ALGORITHM)
#                 token_data = TokenPayload(**payload)
#             except PyJWTError:
#                 # try to decode refresh token
#                 try:
#                     payload = jwt.decode(refresh_token, config.SECRET_KEY, algorithms=ALGORITHM)
#                     token_data = TokenPayload(**payload)
#                     access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
#                     # new access token
#                     new_access_token = create_access_token(
#                         data={"user_id": token_data.user_id},
#                         user_id=token_data.user_id,
#                         expire_delta=access_token_expires
#                     )
#                     print(f'new access token - {new_access_token}')
#                     response = Response(headers=request.headers)
#                     # set new access token
#                     response.set_cookie("access_token", f"Bearer {new_access_token}", access_token_expires,
#                                         httponly=True)
#                     request.state.response = response
#                 except PyJWTError:
#                     response = Response(headers=request.headers)
#                     # remove cookies
#                     response.delete_cookie("access_token")
#                     response.delete_cookie("refresh_token")
#                     print(f'Invalid refresh token - redirect to loginv3')
#                     return RedirectResponse("/loginv3", status_code=status.HTTP_303_SEE_OTHER)
#             user = crud_user.get(db, id=token_data.user_id)
#             if not user:
#                 raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")
#             request.state.user = user
#             return await call_next(request)
#         else:
#             print(f"unprotected path: {request.url}")
#             return await call_next(request)
#     finally:
#             db.close()


# def get_curent_user_from_middleware(request: Request, user: User = Depends(access_token_middleware)):
#     return User


    #         if access_token is not None and refresh_token is not None:
    #             access_token = access_token[7:] if access_token.lower().startswith("bearer") else access_token
    #             refresh_token = refresh_token[7:] if refresh_token.lower().startswith("bearer") else refresh_token
    #
    #         else:
    #             print(f'Some token is missing access token - {access_token}, refresh token {refresh_token}')
    #             response = Response(headers=request.headers)
    #             # remove cookies
    #             response.delete_cookie("access_token")
    #             response.delete_cookie("refresh_token")
    #             return RedirectResponse("/loginv3", status_code=status.HTTP_303_SEE_OTHER)
    #         try:
    #             # try to decode access token
    #             payload = jwt.decode(access_token, config.SECRET_KEY, algorithms=ALGORITHM)
    #             token_data = TokenPayload(**payload)
    #             print(f'Token data seems ok - {token_data.user_id}')
    #         except PyJWTError:
    #             try:
    #                 # try to decode refresh token
    #                 print(f'Error decoding access token - {access_token}')
    #                 payload = jwt.decode(refresh_token, config.SECRET_KEY, algorithms=ALGORITHM)
    #                 token_data = TokenPayload(**payload)
    #                 access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    #                 # new access token
    #                 new_access_token = create_access_token(
    #                     data={"user_id": token_data.user_id},
    #                     user_id=token_data.user_id,
    #                     expire_delta=access_token_expires
    #                 )
    #                 print(f'new access token - {new_access_token}')
    #                 response = Response(headers=request.headers)
    #                 # set new access token
    #                 response.set_cookie("access_token", f"Bearer {new_access_token}", access_token_expires, httponly=True)
    #                 request.state.response = response
    #             except PyJWTError:
    #                 response = Response(headers=request.headers)
    #                 # remove cookies
    #                 response.delete_cookie("access_token")
    #                 response.delete_cookie("refresh_token")
    #                 return RedirectResponse("/loginv3", status_code=status.HTTP_303_SEE_OTHER)
    #
    #         user = crud_user.get(db, id=token_data.user_id)
    #         if not user:
    #             raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")
    #         request.state.user = user
    #         return await call_next(request)
    #     else:
    #         print(f"unprotected path: {request.url}")
    #         return await call_next(request)
    # finally:
    #     db.close()

