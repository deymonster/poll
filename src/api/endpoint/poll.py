from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query, UploadFile, File, Path
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import RedirectResponse, JSONResponse
from motor.motor_asyncio import AsyncIOMotorCollection

from base.schemas import Message
from core.jwt import create_anonymous_user_token

from poll.schemas import QuestionPage, Question, SinglePoll, SinglePollOut, UserSession
from api.utils.security import get_current_user, get_current_active_user, get_poll_session
from api.utils.db import get_db, get_mongo_db
from poll import schemas, service
from poll.service import crud_poll, create_user_session
from user.models import User
from user.schemas import UserBase
from api.utils.logger import PollLogger
# from pkg.mongo_tools.db import mongo_manager

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import locale
from datetime import datetime, timedelta

from uuid import UUID

from api.utils.logger import PollLogger

# Mongo DB

# mongo_db = mongo_manager.get_database()

# Logging
logger = PollLogger(__name__)

router = APIRouter()

current_dir = os.path.dirname(os.path.realpath(__file__))
templates = Jinja2Templates(directory='templates')


# POLLS

# endpoint to get all user polls
@router.get("/user_polls", response_model=List[schemas.Poll])
def user_polls(db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    """
    Эндпоинт для получения списка опросов пользователя

    :param db: Сессия базы данных
    :param user: Текущий пользователь со статусом "Активен"
    :return: Список опросов пользователя
    """
    try:
        polls = service.get_all_user_poll(db=db, user_id=user.id)
        return polls
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Errors while getting user polls - {e}")


# endpoint for adding new poll user for vue frontend
@router.post("/user_polls")
def create_poll(
        poll_data: schemas.CreatePoll, db: Session = Depends(get_db),
        user: User = Depends(get_current_active_user)
):
    """
    Эндпоинт для создания нового опроса cо всеми вопросами и вариантами ответов на них

    :param poll_data: Данные опроса -  название и описание
    :param db: Сессия базы данных
    :param user: Текущий активнеы пользователь
    :return: Созданный опрос
    Пример создания опроса:

        {
    "title": "Новый опрос - 2",
    "description": "Тут описание нового опроса 2",
    "question":
    [
        {"type": "SINGLE ANSWER",
            "text": "Вам была понятна тема урока?",
            "choice": [
                {"text": "Полностью понятна"},
                {"text": "Вообще ничего не понял"},
                {"text": "Частично понял"}]
        },
        {"type": "PLURAL ANSWER",
            "text": "Выберите несколько утверждений, которые вам кажутся верными",
            "choice": [
                {"text": "Земля плоская"},

        {"title": "Название нового опроса1",
        "description": "Тут небольшое описание опроса",
        "poll_cover": "Ссылка на картинку опроса",
        "status_poll": "DRAFT",
        "question": [
            {"type": "SINGLE ANSWER",
            "text": "Сколько вам лет?",
            "choice": [
                {"text": "Мне 10 лет"},
                {"text": "Мне 15 лет"},
                {"text": "Мне 20 лет"}]
        },
        {"type": "PLURAL ANSWER",
            "text": "Выберите несколько утверждений, которые вам кажутся верными",
            "choice": [
                {"text": "Земля плоская"},
                {"text": "Земля круглая"},
                {"text": "Земля квадратная"}]
        }
    ],
    "active_duration": 15,
    "max_participants": 10

},

        ]

    """
    try:
        service.create_new_poll(db=db, poll=poll_data, user_id=user.id)
        return JSONResponse(status_code=201, content={"message": "Poll created successfully"})
    except Exception as e:
        raise HTTPException(status_code=400, detail="Error while creating user poll:" + str(e))


@router.post("/user_polls/{poll_id}/clone", response_model=Message)
def clone_poll_by_id(poll_id: int,
                     db: Session = Depends(get_db),
                     user: User = Depends(get_current_active_user)):
    try:
        service.clone_poll_by_id(db=db, poll_id=poll_id, user_id=user.id)
        return JSONResponse(status_code=201, content={"message": "Poll created successfully"})
    except Exception as e:
        raise HTTPException(status_code=400, detail="Error while creating user poll:" + str(e))


# ednpoint for updating poll
@router.put("/user_polls/{poll_id}", response_model=Message)
def update_poll(poll_id: int,
                poll_data: schemas.UpdatePoll,
                db: Session = Depends(get_db),
                user: User = Depends(get_current_active_user)):
    """
    Эндпойнт для обновления опроса пользователем

    :param poll_id: Идентификатор опроса
    :param poll_data Данные для обновления опроса
    :param db: Сессия базы данных
    :param user: Текущий активный пользователь
    :return message Сообщение об  успешном удалении опроса
    """
    try:
        poll = service.update_poll(db=db, poll_id=poll_id, poll=poll_data, user_id=user.id)
        if poll:
            return JSONResponse(status_code=201, content={"message": "Poll updated successfully"})
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errors while updating poll - {e}")


# endpoint for changing poll status
@router.put("/user_polls/{poll_id}/status", response_model=Message)
def change_poll_status(poll_id: int,
                       payload_status: schemas.PollStatusUpdate,
                       db: Session = Depends(get_db),
                       user: User = Depends(get_current_active_user)):
    """
    Эндпойнт для изменения статуса опроса пользователем

    :param poll_id: Идентификатор опроса
    :param payload_status: Схема для обновления статуса опроса
    :param db: Сессия базы данных
    :param user: Текущий активный пользователь

    """
    try:
        poll = service.update_poll_status(db=db, poll_id=poll_id, payload_status=payload_status, user_id=user.id)
        if poll:
            return JSONResponse(status_code=201,
                                content={"message": "Poll updated successfully", "poll_url": poll.poll_url})
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errors while updating poll - {e}")


# endpoint for deleteing user poll
@router.delete("/user_polls/{poll_id}", response_model=Message)
def delete_user_poll(poll_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    """ Эндпойнт для удаления опроса пользователем
    :param poll_id: Идентификатор опроса
    :param db: Сессия базы данных
    :param user: Текущий активный пользователь
    :return message: Сообщение об  успешном удалении опроса"""
    service.delete_poll_by_user(db=db, poll_id=poll_id, user_id=user.id)
    return JSONResponse(status_code=204, content={"message": "Poll was deleted"})


# Получение детальной информации об опросе
@router.get("/user_polls/{poll_id}")
def get_poll(poll_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)) -> SinglePoll:
    """ Эндпойнт для полуения детальной информации об опросе включая все вопросы и варианты ответы на них
    :param poll_id: Идентификатор опроса
    :param db: Сессия базы данных
    :param user: Текущий активный пользователь
    :return poll  Опрос пользователя со всеми данными"""
    poll = service.get_single_poll(db=db, poll_id=poll_id, user_id=user.id)
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    return poll


# Получение детальной информации об опросе UUID
@router.get("/uuid_poll/{uuid}")
def get_poll(uuid: UUID, db: Session = Depends(get_db)) -> SinglePollOut:
    """ Эндпойнт для получения детальной информации об опросе включая все вопросы и варианты ответы на них для прохождения опроса

    :param uuid: Идентификатор UUID опроса
    :param db: Сессия базы данных
    :return poll  Опрос пользователя со всеми данными

    """
    poll = service.get_poll_by_uuid(db=db, uuid=uuid)

    if not poll:
        raise HTTPException(status_code=404, detail="Published Poll not found")
    return poll


# Генерация анонимного токена для опроса по UUID и по текущему времени
@router.post("/uuid_poll/{uuid}/start")
async def start_poll_session(uuid: UUID,
                             fingerprint: schemas.FingerPrint,
                             db_mongo: AsyncIOMotorCollection = Depends(get_mongo_db),
                             db_mongo_session: UserSession = Depends(get_poll_session),
                             db: Session = Depends(get_db)):
    """ Эндпойнт для создания пользовательской сессии по прохождению опроса


    :param uuid: UUID опроса
    :param fingerprint: Уникальный идентификатор полученный в FingerprintJS
    :param db_mongo: Клиент MongoDB
    :param db_mongo_session: Сессия полученная из Mongo
    :param db: Сессия PostgreSQL
    """

    poll = service.get_poll_by_uuid(db=db, uuid=uuid)
    if not poll:
        raise HTTPException(status_code=404, detail="Published Poll not found")
    if db_mongo_session:
        #  Если пользователь заново перейдет по ссылке опроса и нажмет начать второй раз
        raise HTTPException(status_code=401, detail="Вы уже проходите в данный момент опрос!")

    session_id, token = await create_user_session(db_mongo=db_mongo, poll=poll, fingerprint=fingerprint)
    session_id_str = str(session_id)
    return {
        "token": token,
        "session_id": session_id_str
    }


# RESPONSES
# endpoint for creating response for all poll questions
@router.post("/user_polls/{uuid}/responses", response_model=Message)
async def create_poll_response(uuid: UUID, poll_responses: schemas.CreatePollResponse,
                               db: Session = Depends(get_db),
                               db_mongo: AsyncIOMotorCollection = Depends(get_mongo_db),
                               db_mongo_session: UserSession = Depends(get_poll_session)):
    """
    Эндпойнт для создания ответа на все вопросы опроса


    :param uuid: UUID опроса
    :param poll_responses: Схема для создания ответа на все вопросы опроса
    :param db: Сессия базы данных PostreSQL
    :param db_mongo: Клиент MongoDB
    :param db_mongo_session: Сессия полученная из Mongo
    :return message: Сообщение об  успешном создании ответов на все вопросы опроса
    """
    logger.info(f"Session from MONGO - {db_mongo_session}")
    await service.create_new_response(db=db, db_mongo=db_mongo,
                                      poll_responses=poll_responses, uuid=uuid,
                                      db_mongo_session=db_mongo_session)
    return JSONResponse(status_code=201, content={"message": "Response created successfully"})


# endpoint for getting all responses for poll
@router.get("/user_polls/{poll_id}/responses", response_model=List[schemas.ResponsePayload])
def get_poll_responses(poll_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    """Эндпоинт для получения всех ответов на опрос
    :param poll_id: Идентификатор опроса
    :param db: Сессия базы данных
    :param user: Текущий активный пользователь
    :return: Список ответов на опрос"""
    responses = service.get_all_poll_responses(db=db, poll_id=poll_id, user_id=user.id)
    return responses


# endpoint for getting report from respnonses
@router.get("/user_polls/{poll_id}/report")
def get_poll_report(poll_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    """Эндпоинт для получения отчета по опросу

    :param poll_id: Идентификатор опроса
    :param db: Сессия базы данных
    :param user: Текущий активный пользователь
    :return: Отчет по опросу"""
    report = service.get_poll_report(db=db, poll_id=poll_id)
    return report
