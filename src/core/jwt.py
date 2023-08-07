from datetime import datetime, timedelta

import jwt
import uuid

from core import config

ALGORITHM = "HS256"
access_token_jwt_subject = "access"
refresh_token_jwt_subject = "refresh"


# create access token
def create_access_token(*, data: dict, user_id: str, expire_delta: timedelta = None):
    to_encode = data.copy()
    to_encode.update({"user_id": user_id})
    if expire_delta:
        expire = datetime.utcnow() + expire_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire, "sub": access_token_jwt_subject})
    if "roles" in data:
        to_encode.update({"roles": data["roles"]})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt.decode()


# create refresh token
def create_refresh_token(*, data: dict, user_id: str, expire_delta: timedelta = None):
    to_encode = data.copy()
    to_encode.update({"user_id": user_id})
    if expire_delta:
        expire = datetime.utcnow() + expire_delta
    else:
        expire = datetime.utcnow() + timedelta(days=14)
    to_encode.update({"exp": expire, "sub": refresh_token_jwt_subject})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt.decode()

#

def create_anonymous_user_token():
    data = {
        "exp": datetime.utcnow() + timedelta(minutes=15),  # expiration time
        "iat": datetime.utcnow(), # time the token is generated
        "nbf": datetime.utcnow(), # time before which the token cannot be accepted
        "jti": str(uuid.uuid4()), # unique identifier for the token
        "user_id": str(uuid.uuid4()), # user id the same as jti
    }
    encoded_jwt = jwt.encode(data, config.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

