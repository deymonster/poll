from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from company import models
from api.utils.logger import PollLogger
from core import config
from db.session import SessionLocal
from poll.models import PollStatus, Poll, Response

# Logging
custom_logger = PollLogger(__name__)
logger = PollLogger(__name__)


def check_expired_invitations():
    """
    Запуск планировщика задач для проверки и удаления просроченных приглашений

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


def check_active_polls():
    """
        Запуск планировщика задач для проверки активных опросов
    :return: None
    """
    db = SessionLocal()
    try:
        logger.info(event_type="Checking active polls",
                    obj="",
                    subj=f"{config.PROJECT_NAME}",
                    action="",
                    additional_info=""
                    )
        published_polls = db.query(Poll).filter(Poll.poll_status == PollStatus.PUBLISHED).all()
        for poll in published_polls:
            if poll.is_poll_active() and poll.max_participants is not None:
                participants_count = db.query(Response).filter_by(poll_id=poll.id).count()
                if participants_count >= poll.max_participants:
                    poll.poll_status = PollStatus.CLOSED
        db.commit()

    except Exception as e:
        logger.error(f"Event Type: Проверка активных опросов | Object: {None}"
                     f"| Subject: {config.PROJECT_NAME} | Action: Ошибка при проверке активных опросов"
                     f"| Additional Information: {e}")
    finally:
        db.close()


scheduler = BackgroundScheduler()
scheduler.add_job(check_expired_invitations, 'interval', minutes=15)
# scheduler.add_job(check_active_polls, 'interval', minutes=1)
scheduler.start()
