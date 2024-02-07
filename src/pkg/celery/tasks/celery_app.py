from celery import Celery
from core.config import BROKER_URL, CELERY_RESULT_BACKEND
from api.utils.logger import PollLogger
from celery.schedules import crontab
from datetime import timedelta
from uuid import UUID
# from pkg.celery.tasks.celery_worker import monitor_sessions


# Logging
custom_logger = PollLogger(__name__)
logger = PollLogger(__name__)

celery = Celery(
    'polls',
    broker=BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

#
# def schedule_monitor_sessions(poll_uuid: UUID):
#     logger.info('Begin of schedule_monitor_sessions')
#     task_name = f'monitor-session-{str(poll_uuid)}-every-minute'
#     logger.info(f'Task name - {task_name}')
#
#     # task = celery.task('pkg.celery.tasks.celery_worker.monitor_sessions')
#     celery.add_periodic_task(
#         timedelta(minutes=1),
#         monitor_sessions,
#         args=[poll_uuid],
#         name=task_name
#     )
#     logger.info('Task created!')


celery.conf.beat_schedule = {
    'monitor-poll-every-minute': {
        'task': 'pkg.celery.tasks.celery_worker.monitor_sessions',
        'schedule': timedelta(minutes=1),
        'kwargs': {'poll_uuid': None},
    },
}

celery.conf.timezone = 'UTC'

