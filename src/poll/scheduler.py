import asyncio
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from company import models
from api.utils.logger import PollLogger
from uuid import UUID

from poll.service import get_sessions_by_poll_uuid
from motor.motor_asyncio import AsyncIOMotorCollection
from fastapi import Depends
from api.utils.db import get_db, get_mongo_db

# Logging
custom_logger = PollLogger(__name__)
logger = PollLogger(__name__)


async def check_sessions_expiration(poll_uuid: UUID,  db_mongo: AsyncIOMotorCollection = Depends(get_mongo_db)):
    """
    Запуск мониторинга сессий для конкретного опроса


    :param poll_uuid: ID опроса
    :param db_mongo: Сессия MongoDB
    :return: None
    """
    while True:
        logger.info('Check every session of poll')
        sessions = await get_sessions_by_poll_uuid(db_mongo=db_mongo, poll_uuid=poll_uuid)
        for session in sessions:
            expires_at = session.get("expires_at")
            if expires_at and expires_at <= datetime.utcnow():
                logger.info(f'Session {session} expired!')
                # Сессия истекла, обновляем статус в MongoDB
                db_mongo.update_one(
                    {"_id": session["_id"]},
                    {"$set": {"expired": True}}
                )
        await asyncio.sleep(60)


async def create_task_session_expiration(poll_uuid: UUID, db_mongo: AsyncIOMotorCollection = Depends(get_mongo_db)):
    """
        Создание задачи для мониторинга сессий

        :param poll_uuid: ID опроса
        :param db_mongo: Сессия MongoDB
        """
    logger.info('Session task was created')
    return asyncio.create_task(check_sessions_expiration(poll_uuid, db_mongo))


async def cancel_task_session_expiration(task: asyncio.Task):
    """
    Отмена задачи мониторинга сессий

    :param task: Задача мониторинга сессий
    """
    logger.info('Session task was canceled')
    task.cancel()
    await task


