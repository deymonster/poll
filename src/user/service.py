from typing import Optional, List
from urllib.parse import urlparse
from datetime import datetime
from pathlib import Path
from mimetypes import guess_type
import shutil
from core.local_config import settings

from fastapi import HTTPException, Request, BackgroundTasks, UploadFile

from sqlalchemy.orm import Session

from sqlalchemy import func, extract
from collections import Counter

from base.service import CRUDBase, ModelType
from company.models import Company
from company.service import can_invite_new_users, add_invitation
from core.security import verify_password, get_password_hash
from user.models import User, UserRole
from user.schemas import UserCreate, UserUpdate, UserCreateByEmail,UpdateUserProfile
from api.utils.logger import PollLogger
from utils import generate_registration_token, send_new_account_email, send_update_profile_email

# Logging
logger = PollLogger(__name__)


def check_user_role(user: User, required_roles: List[UserRole]):
    """
    Проверка пользователя на наличие требуемых ролей

    :param user: пользователь
    :param required_roles: список требуемых ролей
    :return: Возвращает пользователя или 403 ошибку
    """

    if not required_roles:
        return user

    if not any(role in user.roles for role in map(lambda r: r.value, required_roles)):
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return user


# def check_license_limit(db_session: Session, company_id: int) -> bool:
#     """
#     Проверка количества лицензий в компании
#
#     :param db_session: сессия БД
#     :param company_id: id компании
#     :return: Возвращает True если есть свободные лицензии, иначе False
#     """
#
#     company = db_session.query(Company).filter(Company.id == company_id).first()
#
#     if not company:
#         raise HTTPException(status_code=404, detail="Company not found")
#     # get all users company with role user
#     # users = db_session.query(User).filter(User.company_id == company_id, User.roles == UserRole.USER).all()
#     # TODO проверить какой способ получения пользователей лучше
#     registered_users_count = len([user for user in company.users if UserRole.USER in user.roles])
#
#     if registered_users_count == company.licenses:
#         return False
#     return True


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def get_by_email(self, db_session: Session, *, email: str) -> Optional[User]:
        """
        Получение пользователя по email

        :param db_session: сессия БД
        :param email: email пользователя
        :return: Возвращает пользователя или None
        """
        query = db_session.query(self.model)
        return query.filter(self.model.email == email).first()

    def create(self, db_session: Session, *, obj_in: UserCreate) -> User:
        """
        Метод создания пользователя

        :param db_session: сессия БД
        :param obj_in: объект создания пользователя
        :return: Возвращает созданного пользователя
        """
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

    def authenticate(
            self, db_session: Session, *, email: str, password: str
    ) -> Optional[User]:
        """
        Метод аутентификации пользователя

        :param db_session: сессия БД
        :param email: email пользователя
        :param password: пароль пользователя
        :return: Возвращает пользователя или None

        """
        user = self.get_by_email(db_session, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def is_active(self, user: User) -> bool:
        """
        Метод проверки активности пользователя

        :param user: пользователь
        :return: Возвращает True если пользователь активен, иначе False

        """
        return user.is_active

    def get_multi(
            self, db_session: Session, current_user: User, *, skip=0, limit=100
    ) -> List[ModelType]:
        """
        Метод получения списка пользователей

        :param db_session: сессия БД
        :param current_user: текущий пользователь
        :param skip:
        :param limit:
        :return: Возвращает список пользователей

        """
        query = db_session.query(self.model)
        if UserRole.ADMIN in current_user.roles:
            query = query.filter(self.model.company_id == current_user.company_id)
        return query.offset(skip).limit(limit).all()

    def get_monthly_users(self, db_session: Session, year: int) -> List[int]:
        """ Метод получения списка пользователей по месяцам

        :param db_session: сессия БД
        :param year: год
        :return: Возвращает список пользователей по месяцам
        """


        users = db_session.query(
        extract('month', self.model.created_at).label('month'),
            ).filter(
                extract('year', self.model.created_at) == year
            ).all()

        # Подсчитываем количество опросов по месяцам
        monthly_counts = Counter(month for month, in users)

        # Инициализируем список нулями для каждого месяца
        monthly_registrations = [monthly_counts[i] for i in range(1, 13)]

        # Общее количество компаний за год - это просто длина списка companies
        total_count = len(users)

        return {
            "monthly_registrations": monthly_registrations,
            "total_count": total_count
        }


    def get_or_404(
            self, db_session: Session, user_id: int, current_user: User
    ) -> ModelType:
        """
        Метод получения пользователя или 404


        :param db_session: сессия БД
        :param user_id: id пользователя
        :param current_user: текущий пользователь
        :return: Возвращает пользователя или 404 ошибку

        """
        user = super().get(db_session, id=user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        # check role if afmin then check if user from same company
        if UserRole.ADMIN in current_user.roles:
            if current_user.company_id != user.company_id:
                raise HTTPException(
                    status_code=403, detail="The user from another company"
                )
        return user

    def update(
            self,
            db_session: Session,
            current_user: User,
            *,
            db_obj: Optional[ModelType] = None,
            update_data: UpdateUserProfile,
            background_tasks: BackgroundTasks
    ) -> ModelType:
        """
        Метод обновления пользователя

        :param db_session: сессия БД
        :param current_user: текущий пользователь
        :param db_obj: объект пользователя которого мы обновляем
        :param update_data: объект обновления пользователя
        :param background_tasks фоновая задача для отправки email
        :return: Возвращает обновленного пользователя

        """

        # User Update His Own Profile
        if not db_obj:
            db_obj = current_user
        # check if user with this email exists and if new email is not the same as in db
        user = self.get_by_email(db_session, email=update_data.email)
        if user and user.id != db_obj.id:
            raise HTTPException(
                status_code=409, detail="The user with this email already exists"
            )

        email_changed = update_data.email is not None and update_data.email != db_obj.email

        email_to = update_data.email if email_changed else db_obj.email
        full_name = update_data.full_name if update_data.full_name is not None else db_obj.full_name

        password_changed = bool(update_data.new_password)
        both_changed = email_changed and password_changed
        roles_changed = update_data.roles is not None and update_data.roles!= db_obj.roles
        role = update_data.roles if roles_changed else db_obj.roles

        # if new password set - check old password hash if ok calculate hash of new password
        if password_changed:
            if not verify_password(update_data.old_password, current_user.hashed_password):
                raise HTTPException(status_code=400, detail="incorrect password")
            update_data.hashed_password = get_password_hash(update_data.new_password)

        match True:
            case _ if UserRole.SUPERADMIN in current_user.roles:
                updated_user = super().update(db_session, db_obj=db_obj, obj_in=update_data)
            case _ if UserRole.ADMIN in current_user.roles:
                if current_user.company_id != db_obj.company_id:
                    raise HTTPException(
                        status_code=403, detail="The user from another company"
                    )
                update_data.roles = [UserRole.USER]
                updated_user = super().update(db_session, db_obj=db_obj, obj_in=update_data)
            case _ if UserRole.USER in current_user.roles:
                if current_user.id != db_obj.id:
                    raise HTTPException(
                        status_code=403, detail="The user can't update another user"
                    )
                update_data.roles = [UserRole.USER]
                # update_data.email = current_user.email
                updated_user = super().update(db_session, db_obj=db_obj, obj_in=update_data)

            case _:
                raise HTTPException(status_code=403, detail="Unknown user role")

        background_tasks.add_task(
            send_update_profile_email,
            email_to=email_to,
            email=email_to,
            full_name=full_name,
            email_changed=email_changed,
            password_changed=password_changed,
            both_changed=both_changed,
            roles_changed=roles_changed,
            role=role
        )
        return updated_user

    # update user his own profile
    def profile_update(
            self,
            db_session: Session,
            user_id: int,
            current_user: User,
            update_data: UpdateUserProfile,
            background_tasks: BackgroundTasks,
            ):
        """
        Метод обновления профиля пользователя

        :param db_session: сессия БД
        :param user_id: id пользователя
        :param current_user: текущий пользователь
        :param update_data: объект обновления профиля пользователя
        :param background_tasks: таск для отправки письма пользователю об обновлении профиля
        :return: Возвращает обновленного пользователя
        """

        email_changed = bool(update_data.email)
        password_changed = bool(update_data.password)
        both_changed = email_changed and password_changed
        if update_data.password:
            if not verify_password(update_data.password, current_user.hashed_password):
                raise HTTPException(status_code=400, detail="Incorrect password")
            current_user.hashed_password = get_password_hash(update_data.new_password)
        if update_data.email:
            user = self.get_by_email(db_session, email=update_data.email)
            if user and user.id != current_user.id:
                raise HTTPException(
                    status_code=409, detail="The user with this email already exists"
                )
            current_user.email = update_data.email
        if update_data.avatar:
            current_user.avatar = update_data.avatar
        db_session.commit()
        db_session.refresh(current_user)
        return current_user


    # delete user by id depends on role
    def crud_remove(self, db: Session, user_id: int, current_user: User):
        """Метод удаления пользователя

        :param db: сессия БД
        :param user_id: id пользователя
        :param current_user: текущий пользователь
        :return: вызывает базовый метод удаления пользователя

        """
        user = self.get_or_404(db, user_id=user_id, current_user=current_user)
        if UserRole.ADMIN in current_user.roles:
            if current_user.company_id != user.company_id:
                raise HTTPException(
                    status_code=403, detail="The user from another company"
                )
            return super().remove(db, id=user_id)
        return super().remove(db, id=user_id)

    # register user by email
    def register_user(
            self,
            db_session: Session,
            request: Request,
            current_user: User,
            *,
            obj_in: UserCreateByEmail,
            background_tasks: BackgroundTasks,
    ):
        """
        Метод регистрации пользователя

        :param db_session: сессия БД
        :param request: запрос
        :param current_user: текущий пользователь
        :param obj_in: объект создания пользователя
        :param background_tasks: фоновые задачи для отправки письма
        :return: Возвращает сообщение об успешной отправке письма

        """

        if self.get_by_email(db_session=db_session, email=obj_in.email):
            raise HTTPException(
                status_code=409,
                detail="The user with this username already exists in the system.",
            )
        match True:
            case _ if UserRole.ADMIN in current_user.roles:
                if not can_invite_new_users(
                        db=db_session, company_id=current_user.company_id
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="The company has no free licenses.",
                    )
                obj_in.roles = [UserRole.USER]
            case _ if UserRole.SUPERADMIN in current_user.roles:
                if UserRole.ADMIN in obj_in.roles:
                    obj_in.roles = [UserRole.ADMIN]
                if UserRole.SUPERADMIN in obj_in.roles:
                    obj_in.roles = [UserRole.SUPERADMIN]
                if UserRole.USER in obj_in.roles:
                    obj_in.roles = [UserRole.USER]

            case _:
                raise HTTPException(status_code=403, detail="Unknown user role")
        registration_token = generate_registration_token(
            email=obj_in.email,
            roles=obj_in.roles,
            full_name=obj_in.full_name,
            company_id=obj_in.company_id,
        )
        if isinstance(registration_token, bytes):
            registration_token = registration_token.decode("utf-8")

        add_invitation(
            db=db_session,
            email=obj_in.email,
            token=registration_token,
            company_id=obj_in.company_id,
        )
        referer = request.headers.get("Referer")
        frontend_url = f"{urlparse(referer).scheme}://{urlparse(referer).netloc}"

        # send email with registration link in background
        background_tasks.add_task(
            send_new_account_email,
            email_to=obj_in.email,
            full_name=obj_in.full_name,
            email=obj_in.email,
            link=frontend_url,
            token=registration_token,
        )

        logger.info(
            event_type="User registration",
            obj=f"{current_user.full_name}",
            subj=f"{obj_in.full_name}",
            action="Registration email sent to user",
            additional_info=f"User role for new user - {obj_in.roles}",
        )

        return {"message": "Registration email sent to user"}

    def upload_user_avatar(self, db_session: Session, file: UploadFile, user_id: int, current_user: User):
        """"
        Метод для загрузки изображения аватарки на сервер


        :param db_session: Сессия БД
        :param file: Загружаемый файл
        :param user_id: ID пользователя
        :param current_user:  Текущий пользователь
        :return Path: полный путь до изображения
        """

        # max size file 5 Mb
        max_file_size = 5 * 1024 * 1024
        file_size = file.file.seek(0, 2)
        if file_size > max_file_size:
            raise HTTPException(status_code=413, detail="File is too large")
        # check if file is an image
        mime_type, _ = guess_type(file.filename)
        if not mime_type or not mime_type.startswith("image"):
            raise HTTPException(status_code=415, detail="Unsupported media type")

        user = self.get_or_404(db_session=db_session, user_id=user_id, current_user=current_user)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user_dir = Path(settings.MEDIA_ROOT) / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)

        file_name = f"{user_id}_{file.filename}"
        path = user_dir / file_name
        file.file.seek(0)
        try:
            with open(path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except IOError as e:
            raise HTTPException(status_code=500, detail=f"Could not upload file: {e}")

        return file_name


crud_user = CRUDUser(User)
