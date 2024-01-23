from datetime import datetime, timedelta

import jwt
import uuid

from core import config

ALGORITHM = "HS256"
access_token_jwt_subject = "access"
refresh_token_jwt_subject = "refresh"
anonymous_token_jwt_subject = "anonym"


# create access token
# def create_access_token(*, data: dict, user_id: str, expire_delta: timedelta = None):
#     to_encode = data.copy()
#     to_encode.update({"user_id": user_id})
#     if expire_delta:
#         expire = datetime.utcnow() + expire_delta
#     else:
#         expire = datetime.utcnow() + timedelta(minutes=15)
#     to_encode.update({"exp": expire, "sub": access_token_jwt_subject})
#     if "roles" in data:
#         to_encode.update({"roles": data["roles"]})
#     encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=ALGORITHM)
#     return encoded_jwt.decode()

def create_access_token(data: dict, expire_delta: timedelta = None):
    """ Create access token

    :param data: Dataclass with useful info about user
    :param expire_delta: timedelta - time to live access token
    :return access token: str
    """
    to_encode = data.copy()
    if expire_delta:
        expire = datetime.utcnow() + expire_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire, "sub": access_token_jwt_subject})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt.decode()


# create refresh token
def create_refresh_token(data: dict, expire_delta: timedelta = None):
    to_encode = data.copy()
    if expire_delta:
        expire = datetime.utcnow() + expire_delta
    else:
        expire = datetime.utcnow() + timedelta(days=14)
    to_encode.update({"exp": expire, "sub": refresh_token_jwt_subject})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt.decode()


def create_anonymous_user_token(data: dict):
    current_time = datetime.utcnow()
    to_encode = data.copy()
    to_encode.update({"sub": anonymous_token_jwt_subject,
                      "timestamp": current_time.timestamp()})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt.decode()

