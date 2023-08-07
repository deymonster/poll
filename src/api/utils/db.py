from starlette.requests import Request
from db.session import SessionLocal


def get_db_middleware():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db(request: Request):
    return request.state.db
