from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from base.service import CRUDBase, ModelType
from company.models import Company
from core.security import verify_password, get_password_hash
from user.models import User, UserRole
from user.schemas import UserCreate, UserUpdate, UserCreateByEmail
from api.utils.logger import PollLogger

# Logging
logger = PollLogger(__name__).get_logger()


def check_user_role(user: User, required_roles: List[UserRole]):
    """
    Проверка пользователя на наличие требуемых ролей
    """

    if not required_roles:
        return user

    if not any(role in user.roles for role in map(lambda r: r.value, required_roles)):
        raise HTTPException(status_code=403, detail="The user doesn't have enough privileges")
    return user


def check_license_limit(self, db_session: Session, company_id: int) -> bool:
    """
    Проверка количества лицензий в компании

    :param db_session: сессия БД
    :param company_id: id компании
    :return: Возвращает True если есть свободные лицензии, иначе False
    """

    company = db_session.query(Company).filter(Company.id == company_id).first()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    # get all users company with role user
    # users = db_session.query(User).filter(User.company_id == company_id, User.roles == UserRole.USER).all()
    # TODO проверить какой способ получения пользователей лучше
    registered_users_count = len([user for user in company.users if UserRole.USER in user.roles])

    if registered_users_count == company.licenses:
        return False
    return True


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):

    def get_by_email(self, db_session: Session, *, email: str) -> Optional[User]:
        query = db_session.query(self.model)
        user = query.filter(self.model.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="The user with this email does not exist in the system")
        return user

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
        """Создание пользователя
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

    def authenticate(self, db_session: Session, *, email: str, password: str) -> Optional[User]:
        user = self.get_by_email(db_session, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def is_active(self, user: User) -> bool:
        return user.is_active

    def get_multi(self, db_session: Session, current_user: User, *, skip=0, limit=100) -> List[ModelType]:
        """Метод получения списка пользователей

        :param db_session: сессия БД
        :param current_user: текущий пользователь
        :param skip: пропустить
        :param limit: лимит
        :return: Возвращает список пользователей

        Если пользователь с ролью админ, то получаем список пользователей только из его компании
        Инача получаем всех пользователей"""
        query = db_session.query(self.model)
        if UserRole.ADMIN in current_user.roles:
            query = query.filter(self.model.company_id == current_user.company_id)
        return query.offset(skip).limit(limit).all()

    def get_or_404(self, db_session: Session, user_id: int, current_user: User) -> ModelType:
        """Метод получения пользователя или 404
        :param db_session: сессия БД
        :param user_id: id пользователя
        :param current_user: текущий пользователь
        :return: Возвращает пользователя или 404 ошибку

        1. Получаем пользователя по id
        2. Если пользователь не найден, то возвращаем 404 ошибку
        3. Если роль админ, то проверяем, что пользователь из той же компании
        4. Если роль суперадмин то возвращаем пользователя
        """
        user = super().get(db_session, id=user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        # check role if afmin then check if user from same company
        if UserRole.ADMIN in current_user.roles:
            if current_user.company_id != user.company_id:
                raise HTTPException(status_code=403, detail="The user from another company")
        return user

    def update(self, db_session: Session, current_user: User, *, db_obj: Optional[ModelType] = None, update_data: UserUpdate) -> ModelType:
        """Метод обновления пользователя

        :param db_session: сессия БД
        :param current_user: текущий пользователь
        :param db_obj: объект пользователя
        :param update_data: объект обновления пользователя
        :return: Возвращает обновленного пользователя

        1. Проверяем, существует ли пользователь с таким же email
        2. Если роль админ, то проверяем, что пользователь из той же компании
        3. Если роль суперадмин то обновляем пользователя
        4. Если роль юзер, то проверяем, что пользователь обновляет сам себя и принудительно меняем опять его роль на USER
        """
        if not db_obj:
            db_obj = current_user
        # check if user with this email exists and if new email is not the same as in db
        user = self.get_by_email(db_session, email=update_data.email)
        if user and user.id != db_obj.id:
            raise HTTPException(status_code=409, detail="The user with this email already exists")
        # if role admin then check if user from same company
        if UserRole.ADMIN in current_user.roles:
            if current_user.company_id != db_obj.company_id:
                raise HTTPException(status_code=403, detail="The user from another company")
            return super().update(db_session, db_obj=db_obj, obj_in=update_data)
        # if role super admin then update anyway
        if UserRole.SUPERADMIN in current_user.roles:
            return super().update(db_session, db_obj=db_obj, obj_in=update_data)
        # if role user then check if user is himself
        if UserRole.USER and current_user.id != db_obj.id:
            raise HTTPException(status_code=403, detail="The user can't update another user")
        update_data.roles = [UserRole.USER]
        return super().update(db_session, db_obj=db_obj, obj_in=update_data)

    # delete user by id depends on role
    def crud_remove(self, db: Session, user_id: int, current_user: User):
        """Метод удаления пользователя
        :param db: сессия БД
        :param user_id: id пользователя
        :param current_user: текущий пользователь
        :return:
        """
        user = self.get_or_404(db, user_id=user_id, current_user=current_user)
        if UserRole.ADMIN in current_user.roles:
            if current_user.company_id != user.company_id:
                raise HTTPException(status_code=403, detail="The user from another company")
            return super().remove(db, id=user_id)
        return super().remove(db, id=user_id)



crud_user = CRUDUser(User)
