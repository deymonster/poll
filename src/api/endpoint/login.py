import json
from datetime import timedelta

import jwt
from jwt import PyJWTError
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from starlette import status
from starlette.requests import Request

from core import config
from core.jwt import create_access_token, create_refresh_token, ALGORITHM
from core.security import get_password_hash

from api.utils.db import get_db
from api.utils.security import get_current_user
from base.schemas import Msg, Token, TokenPayload
from user.models import User as DBUser
from user.schemas import User
from user.service import crud_user
from utils import (generate_password_reset_token,
                   send_reset_password_email, verify_password_reset_token)
from starlette.responses import Response, RedirectResponse, JSONResponse
from fastapi.responses import HTMLResponse

router = APIRouter()


# endpoint to login with  vue js
@router.post("/login",summary="Авторизация", description="Авторизация пользователя в системе")
def login_access_token_vue(request: Request, response: Response, db: Session = Depends(get_db),
                           form_data: OAuth2PasswordRequestForm = Depends()):
    user = crud_user.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not crud_user.is_active(user):
        raise HTTPException(status_code=400, detail="Inactive user")

    # generate access token
    access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "roles": user.roles}, user_id=user.id, expire_delta=access_token_expires
    )
    # generate refresh token
    refresh_token_expires = timedelta(minutes=config.REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = create_refresh_token(
        data={"sub": user.email}, user_id=user.id, expire_delta=refresh_token_expires
    )
    # set tokens in cookies
    response.set_cookie(key="Authorization", value=f"Bearer {access_token}", httponly=True)
    response.set_cookie(key="Authorization_refresh", value=f"Bearer {refresh_token}", httponly=True)
    return {
        "message": "Login successfull",
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


# endpoint for refresh token for vue js
@router.post("/refresh")
def login_refresh_token_vue(refresh_token: str, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(refresh_token, config.SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        token_data = TokenPayload(user_id=user_id)
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


@router.post("/access-token", deprecated=True)
def login_access_token(response: Response,
                       db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = crud_user.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not crud_user.is_active(user):
        raise HTTPException(status_code=400, detail="Inactive user")
    # generate access token
    access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, user_id=user.id, expire_delta=access_token_expires
    )
    # generate refresh token
    refresh_token_expires = timedelta(minutes=config.REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = create_refresh_token(
        data={"sub": user.email}, user_id=user.id, expire_delta=refresh_token_expires
    )
    # set token to cookies and set object response with success status

    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        domain="127.0.0.1",
        # secure=True,
        # path="/",
        samesite="Strict"
    )
    response.set_cookie(
        key="refresh_token",
        value=f"Bearer {refresh_token}",
        httponly=True,
        domain="127.0.0.1",
        # secure=True,
        # path="/",
        samesite="Strict"
    )
    # set response headers
    response.headers["location"] = "http://127.0.0.1:8000/polls/"
    response.status_code = status.HTTP_303_SEE_OTHER
    return response


# @router.post("/token/refresh/")
# def refresh_token(response: Response, db: Session = Depends(get_db), refresh_token: str = Depends(reusable_oauth2)):
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"}
#     )
#     try:
#         payload = jwt.decode(refresh_token, config.SECRET_KEY, algorithms=ALGORITHM)
#         user_id: str = payload.get("user_id")
#         if user_id is None:
#             raise credentials_exception
#         token_data = TokenPayload(user_id=user_id)
#     except PyJWTError:
#         raise credentials_exception
#     user = crud_user.get(db, id=token_data.user_id)
#     if user is None:
#         raise credentials_exception
#     refresh_token_expires = timedelta(minutes=config.REFRESH_TOKEN_EXPIRE_MINUTES)
#     new_refresh_token = create_refresh_token(
#         data={"sub": user.email}, user_id=user_id, expire_delta=refresh_token_expires
#     )
#     acces_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
#     new_access_token = create_access_token(
#         data={"sub": user.email}, user_id=user_id, expire_delta=acces_token_expires
#     )
#     response.set_cookie(
#         key="access_token",
#         value=f"Bearer {new_access_token}",
#         httponly=True,
#         domain="127.0.0.1",
#         # secure=True,
#         # path="/",
#         samesite="Strict"
#     )
#     response.set_cookie(
#         key="refresh_token",
#         value=f"Bearer {new_refresh_token}",
#         httponly=True,
#         domain="127.0.0.1",
#         # secure=True,
#         # path="/",
#         samesite="Strict"
#     )
#     return response


@router.post("/test_access_token", response_model=User, deprecated=True)
def test_token(current_user: DBUser = Depends(get_current_user)):
    """
    Test access token
    """
    return current_user


@router.post("/password-recovery/{email}", response_model=Msg)
def recover_password(email: str, db: Session = Depends(get_db)):
    """
    Password Recovery
    """
    user = crud_user.get_by_email(db, email=email)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system.",
        )
    password_reset_token = generate_password_reset_token(email=email)
    send_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )
    return {"msg": "Password recovery email sent"}


@router.post("/reset-password/", response_model=Msg)
def reset_password(token: str = Body(...), new_password: str = Body(...), db: Session = Depends(get_db)):
    """
    Reset password
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
