from starlette.requests import Request

from api.utils.logger import PollLogger
from db.session import SessionLocal



# Logging
logger = PollLogger(__name__)


def get_db_middleware():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db(request: Request):
    return request.state.db


async def get_mongo_db(request: Request):
    return request.state.mongo_db


# async def get_db_mongo(request: Request, call_next):
#     await mongo_manager.connect_to_database()
#     request.state.db_mongo = mongo_manager.get_database()
#     response = await call_next(request)
#     await mongo_manager.close_database_connection()
#     return response





