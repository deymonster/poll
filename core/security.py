from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Функция для проверки пароля на соответствие хэшу
def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


# Функция для создания хэша пароля
def get_password_hash(password: str):
    return pwd_context.hash(password)