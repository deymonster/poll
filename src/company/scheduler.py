from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from company import models
from api.utils.logger import PollLogger
from db.session import SessionLocal

# Logging
logger = PollLogger(__name__).get_logger()


def check_expired_invitations():
    """
    Запуск планировщика задач для проверки и удаления просроченных приглашений

    :param db: Сессия БД
    :return: None
    """
    db = SessionLocal()
    logger.info(f'Begin to Check expired invitations')
    try:
        expired_invitations = db.query(models.Invitations).filter(models.Invitations.expires_at < datetime.utcnow()).all()
        for invitation in expired_invitations:
            logger.info(f'Delete invitation {invitation.email}')
            db.delete(invitation)
        db.commit()
        logger.info(f'End to Check expired invitations')
    except Exception as e:
        logger.error(f'Error in check_expired_invitations: {e}')
    finally:
        db.close()


scheduler = BackgroundScheduler()
scheduler.add_job(check_expired_invitations, 'interval', minutes=15)
scheduler.start()
