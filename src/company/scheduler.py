from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
from sqlalchemy.orm import Session
from company import models
from api.utils.logger import PollLogger
from core import config
from db.session import SessionLocal
from pkg.mongo_tools.db import get_mongo_collection
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


async def check_active_polls():
    """
    Запуск планировщика задач для проверки активных опросов
    """
    db = SessionLocal()
    collection = get_mongo_collection()
    try:
        logger.info(event_type="Checking active polls",
                    obj="",
                    subj=f"{config.PROJECT_NAME}",
                    action="",
                    additional_info=""
                    )
        published_polls = db.query(Poll).filter(Poll.poll_status == PollStatus.PUBLISHED).all()
        current_time = datetime.utcnow()
        for poll in published_polls:
            async for session in collection.find({"poll_uuid": str(poll.uuid), "expired": False}):
                if 'expires_at' in session and session['expires_at'] is not None and session['expires_at'] < current_time:
                    await collection.update_one(
                            {"_id": session['_id']},
                            {"$set": {"expired": True}}
                    )
                    logger.info(f"Session {session['_id']} for poll {poll.uuid} has been marked as expired")
    except Exception as e:
        logger.error(f"Event Type: Проверка активных опросов | Object: {None}"
                     f"| Subject: {config.PROJECT_NAME} | Action: Ошибка при проверке активных опросов"
                     f"| Additional Information: {e}")
    finally:
        db.close()


scheduler = AsyncIOScheduler()
scheduler.add_job(check_expired_invitations, 'interval', minutes=15)
scheduler.add_job(check_active_polls, 'interval', seconds=5)
scheduler.start()
