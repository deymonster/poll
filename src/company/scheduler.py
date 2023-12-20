from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from company import models
from api.utils.logger import PollLogger
from core import config
from db.session import SessionLocal

# Logging
custom_logger = PollLogger(__name__)
logger = PollLogger(__name__)


def check_expired_invitations():
    """
    Запуск планировщика задач для проверки и удаления просроченных приглашений

    :param db: Сессия БД
    :return: None
    """
    db = SessionLocal()
    try:
        logger.info(event_type="Checking invitation",
                    obj="",
                    subj=f"{config.PROJECT_NAME}",
                    action="",
                    additional_info=""
                    )
        # custom_logger.log_event(event_type="Проверка приглашений",
        #                         object_info="",
        #                         subject_info=f"{config.PROJECT_NAME}",
        #                         action_info="",
        #                         additional_info="")
        expired_invitations = db.query(models.Invitations).filter(models.Invitations.expires_at < datetime.utcnow()).all()
        for invitation in expired_invitations:
            # logger.info(f'Delete invitation {invitation.email}')
            db.delete(invitation)
        db.commit()

    except Exception as e:

        logger.error(f"Event Type: Проверка приглашений | Object: {None}"
                     f"| Subject: {config.PROJECT_NAME} | Action: Ошибка при проверке просроченных приглашений"
                     f"| Additional Information: {e}")
    finally:
        db.close()


scheduler = BackgroundScheduler()
scheduler.add_job(check_expired_invitations, 'interval', minutes=15)
scheduler.start()
