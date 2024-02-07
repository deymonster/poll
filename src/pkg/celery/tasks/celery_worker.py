import asyncio

from db.session import SessionLocal
from .celery_app import celery
from sqlalchemy.orm import Session
from api.utils.logger import PollLogger
from poll.models import PollStatus, Poll, Response
from uuid import UUID
from celery.exceptions import SoftTimeLimitExceeded
from motor.motor_asyncio import AsyncIOMotorCollection
from datetime import datetime

from ...mongo_tools.db import session_collection

# Logging
custom_logger = PollLogger(__name__)
logger = PollLogger(__name__)

#
# @celery.task
# def monitor_poll(poll_uuid: UUID):
#     db = SessionLocal()
#     try:
#
#         if poll_uuid is not None:
#             logger.info(f'Celery task for poll {poll_uuid}')
#             poll = db.query(Poll).filter_by(uuid=poll_uuid).first()
#             if poll and poll.poll_status == PollStatus.CLOSED:
#                 logger.info(f'The poll {poll_uuid} is already closed. Exiting task.')
#                 return
#
#             if poll:
#                 if poll.is_published() and poll.max_participants is not None:
#                     participants_count = db.query(Response).filter_by(poll_id=poll.id).count()
#                     if participants_count == poll.max_participants:
#                         poll.poll_status = PollStatus.CLOSED
#                         db.commit()
#         else:
#             logger.info(f'Celery task for all polls')
#     except SoftTimeLimitExceeded:
#         logger.error("Task execution time exceeded")
#     except Exception as e:
#         logger.error(f"Error in Celery task: {str(e)}")

#
# @celery.on_after_finalize.connect
# def setup_periodic_tasks(sender, **kwargs):
#     # Calls test('hello') every 10 seconds.
#     sender.add_periodic_task(10.0, test.s('hello'))
#
#
# @celery.task
# def test(arg):
#     print(arg)


@celery.task
def monitor_sessions(poll_uuid: UUID):
    db = SessionLocal()
    db_mongo = session_collection
    loop = asyncio.get_event_loop()

    try:
        sessions = loop.run_until_complete(db_mongo.find({"poll_uuid": str(poll_uuid)}).to_list(length=None))

        logger.info(f'All sessions of poll- {sessions}')
        for session in sessions:
            expires_at = session.get("expires_at")
            if expires_at and expires_at <= datetime.utcnow():
                logger.info(f'Session {session} expired!')
                # Сессия истекла, обновляем статус в MongoDB
                db_mongo.update_one(
                    {"_id": session["_id"]},
                    {"$set": {"expired": True}}
                )
    except Exception as e:
        logger.error(f'Mongo error while updating session - {e}')




