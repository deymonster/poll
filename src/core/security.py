from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Функция для проверки пароля на соответствие хэшу
def verify_password(plain_password: str, hashed_password: str):
    """Функция для проверки пароля на соответствие хэшу

    :param plain_password: <PASSWORD>
    :param hashed_password: <PASSWORD>
    :return: True если пароль соответствует хэшу, иначе False
    """

    return pwd_context.verify(plain_password, hashed_password)


# Функция для создания хэша пароля
def get_password_hash(password: str):
    """Функция для создания хэша пароля

    :param password: <PASSWORD>
    :return: хэш пароля
    """

    return pwd_context.hash(password)