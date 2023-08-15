from typing import Optional
from sqlalchemy.orm import Session

from base.service import CRUDBase
from core.security import verify_password, get_password_hash
from user.models import User
from user.schemas import UserCreate, UserUpdate, UserCreateByEmail


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):

    def get_by_email(self, db_session: Session, *, email: str) -> Optional[User]:
        return db_session.query(User).filter(User.email == email).first()

    def create(self, db_session: Session, *, obj_in: UserCreate) -> User:
        db_obj = User(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            full_name=obj_in.full_name,
            roles=obj_in.roles,
        )
        db_session.add(db_obj)
        db_session.commit()
        db_session.refresh(db_obj)
        return db_obj

    # method for create user by sending email with token, after that user can set password
    def create_user_by_email(self, db_session: Session, *, obj_in: UserCreateByEmail) -> User:
        """ Создание пользователя
        1. Проверяем, существует ли пользователь с таким же email
        2. Если пользователь существует, то возвращаем ошибку
        3. Если пользователь не существует, то генеририруем токен, отправляем письмо со ссылкой с токеном

        """
        db_obj = User(
            email=obj_in.email,
            full_name=obj_in.full_name,
        )
        db_session.add(db_obj)
        db_session.commit()
        db_session.refresh(db_obj)
        return db_obj

    def authenticate(
            self, db_session: Session, *, email: str, password: str
                     ) -> Optional[User]:
        user = self.get_by_email(db_session, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def is_active(self, user: User) -> bool:
        return user.is_active

    def is_superuser(self, user: User) -> bool:
        return user.is_superuser


crud_user = CRUDUser(User)

