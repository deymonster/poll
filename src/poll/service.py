import shutil

import copy
from datetime import datetime, timezone, timedelta

import bson
from fastapi import HTTPException, UploadFile, Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, desc
from starlette.responses import RedirectResponse, JSONResponse
from starlette import status

from sqlalchemy.orm import Session, joinedload, class_mapper, RelationshipProperty
from motor.motor_asyncio import AsyncIOMotorCollection
from sqlalchemy.orm.session import make_transient

from api.utils.db import get_mongo_db
from core.jwt import create_anonymous_user_token
from core.local_config import settings
# from pkg.mongo_tools.db import mongo_manager

from . import models, schemas
from typing import List, Union
from base.service import CRUDBase
from mimetypes import guess_type
from typing import Optional

from uuid import UUID, uuid4

from .models import PollStatus, Response
from .schemas import QuestionType, StatusPoll
from api.utils.logger import PollLogger
from .session_data import SessionData

# Logging
logger = PollLogger(__name__)


def sqlalchemy_to_pydantic(poll: models.Poll):
    """ Типа костыль для преобразования инстанса модели опроса в модель Pydantic"""
    questions = []
    for db_question in poll.question:
        choices = []
        for db_choice in db_question.choice:
            choice_pydantic = schemas.Choice(
                text=db_choice.text,
                choice_cover=db_choice.choice_cover
            )
            choices.append(choice_pydantic)
        question_pydantic = schemas.Question(
            type=db_question.type,
            text=db_question.text,
            choice=choices
        )
        questions.append(question_pydantic)
    poll_pydantic = schemas.CreatePoll(
        title=poll.title,
        description=poll.description,
        poll_cover=poll.poll_cover,
        poll_status=poll.poll_status,
        question=questions
    )
    return poll_pydantic


# TODO доделать класс CRUDBase для Poll
class CRUDPoll(CRUDBase[schemas.Poll, schemas.CreatePoll, schemas.UpdatePoll]):
    # create new poll with questions

    def create_new_poll(self, db: Session, *, poll: schemas.CreatePoll, user_id: int):
        print(poll)
        with db.begin_nested():
            db_poll = models.Poll(**poll.dict(exclude={"questions"}), user_id=user_id)
            db.add(db_poll)
            db.flush()
            create_question(db=db, questions=poll.question, poll_id=db_poll.id)
            db.refresh(db_poll)
        db.commit()
        return db_poll


crud_poll = CRUDPoll(models.Poll)


# POLL

# get single poll by id with questions and choices
def get_single_poll(db: Session, poll_id: int, user_id: int):
    """ Get user poll with all questions and choices in it"""
    return (
        db.query(models.Poll)
        .options(joinedload(models.Poll.question)
                 .joinedload(models.Question.choice))
        .filter(models.Poll.id == poll_id)
        .filter(models.Poll.user_id == user_id)
        .first())


# get single poll by uuid with questions and choices
def get_poll_by_uuid(db: Session, uuid: UUID):
    """ Get user poll with all questions and choices in it by UUID"""
    poll = db.query(models.Poll) \
        .options(joinedload(models.Poll.question)
                 .joinedload(models.Question.choice)) \
        .filter(models.Poll.uuid == uuid).first()
    if poll is None:
        raise HTTPException(status_code=404, detail="Poll not found")
    if poll.poll_url and poll.poll_status == PollStatus.PUBLISHED:
        return poll
    elif poll.poll_status in [PollStatus.ENDED]:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "poll-closed",
                "message": "Опрос завершен.",
                "poll_status": poll.poll_status,
                "poll_name": poll.title
            }
        )


# create list questions with nested choices - for creating poll
def create_question(db: Session, questions: List[schemas.Question], poll_id: int) -> None:
    db_questions = []

    for question in questions:
        db_question = models.Question(**question.model_dump(exclude={"choice"}), poll_id=poll_id)

        db.add(db_question)
        db.flush()
        db.refresh(db_question)
        db_choice = [models.Choice(**choice.model_dump(), question_id=db_question.id) for choice in question.choice]
        db.add_all(db_choice)
        db_questions.append(db_question)
    db.commit()


# create new poll with questions and choices
def create_new_poll(db: Session, poll: schemas.CreatePoll, user_id: int):
    """
    Создание нового опроса с вопросами и вариантами ответа

    :param db: Session
    :param poll: schemas.CreatePoll
    :param user_id: int
    :return: Model Poll
    """
    db_poll = models.Poll(**poll.model_dump(exclude={"question"}), user_id=user_id)
    if poll.poll_status == StatusPoll.PUBLISHED:
        db_poll.poll_url = f"/poll/{db_poll.uuid}"
    db.add(db_poll)
    db.commit()
    db.refresh(db_poll)
    create_question(db=db, questions=poll.question, poll_id=db_poll.id)
    return db_poll


# create new poll with title and description only
def create_new_simple_poll(db: Session, poll: schemas.CreateSimplePoll, user_id: int):
    """
    Создание нового опроса с название и описанием

    :param db: сессия БД
    :param poll: схема опроса
    :param user_id: id пользователя
    :return: созданный опрос
    """
    db_poll = models.Poll(**poll.model_dump(), user_id=user_id)
    db.add(db_poll)
    db.commit()
    # change poll_url with uuid
    db_poll.poll_url = f"/poll/{db_poll.uuid}"
    db.commit()
    db.refresh(db_poll)
    return db_poll


def clone_poll_by_id(db: Session, poll_id, user_id: int):
    """ Клонирование опроса из существующего

    :param db: Session DB
    :param poll_id: Poll ID
    :param user_id: User ID
    :return new_poll: Poll
    """
    original_poll = get_single_poll(db, poll_id, user_id)
    if original_poll is None:
        raise HTTPException(status_code=404, detail="Poll not found")

    poll_pydantic_instance = sqlalchemy_to_pydantic(original_poll)
    new_uuid = uuid4()

    # Исключаем created_at из данных
    original_poll_data = poll_pydantic_instance.model_dump(exclude={"created_at"})
    # Устанавливаем новый UUID
    original_poll_data["uuid"] = new_uuid
    # Устанавливаем значения по умолчанию
    original_poll_data["poll_status"] = PollStatus.DRAFT
    original_poll_data["poll_url"] = ''
    # Создаем новый опрос с вопросами и вариантами ответов
    new_poll = create_new_poll(db, schemas.CreatePoll(**original_poll_data), user_id)

    return new_poll


# get all user polls
def get_all_user_poll(db: Session, user_id: int, status: Optional[PollStatus] = None):
    """
    Получаем все опросы пользователя

    :param db: Session
    :param user_id: int
    :param status: PollStatus (optional)
    :return: List[Model Poll]
    """
    selected_fields = [models.Poll.id, models.Poll.uuid, models.Poll.created_at, models.Poll.title,
                       models.Poll.description,
                       models.Poll.poll_cover, models.Poll.poll_status]
    query = db.query(*selected_fields).filter(models.Poll.user_id == user_id)

    if status:
        query = query.filter(models.Poll.poll_status == status)
    query = query.order_by(desc(models.Poll.created_at))
    return query.all()


# get single poll with list of responses
def get_single_poll_with_response(db: Session, poll_id: int, user_id: int):
    return db.query(models.Response).filter(models.Poll.id == poll_id).all()


# get single poll with count of questions
def get_poll_detail(db: Session, poll_id: int, user_id: int):
    poll = db.query(models.Poll).filter(models.Poll.id == poll_id).filter(models.Poll.user_id == user_id).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    poll_data = {
        "created_at": poll.created_at,
        "title": poll.title,
        "description": poll.description,
        "poll_cover": poll.poll_cover,
        "is_active": poll.is_active,
        "poll_url": poll.poll_url,
        "user_id": user_id,
        "question_count": db.query(models.Question).filter(models.Question.poll_id == poll_id).count()}
    # logger.info(poll_data)
    return poll_data


def update_poll(db: Session, poll_id: int, poll: schemas.UpdatePoll, user_id: int):
    """"
    Обновление опроса

    :param db: сессия БД
    :param poll_id: id опроса
    :param poll: схема обновления
    :param user_id: id пользователя
    :return: обновленный опрос

    """

    # проверка на существование опроса в БД
    db_poll = db.query(models.Poll).options(joinedload(models.Poll.question).joinedload(models.Question.choice)) \
        .filter(models.Poll.id == poll_id).filter(models.Poll.user_id == user_id).first()

    if not db_poll:
        raise HTTPException(status_code=404, detail="Poll not found")

    # Проверяем статус опроса
    if db_poll.poll_status != PollStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Cannot update a non-draft poll")

    #  otherwise update poll
    for attr, value in poll.model_dump(exclude={"question"}).items():
        if value is not None:
            setattr(db_poll, attr, value)

    # Если статус Published то генерируем ссылку
    if poll.poll_status == StatusPoll.PUBLISHED:
        db_poll.poll_url == f"/poll/{db_poll.uuid}"

    # Удаляем все связанные варианты ответов
    db.query(models.Choice).filter(models.Choice.question_id.in_(
        db.query(models.Question.id).filter(models.Question.poll_id == poll_id)
    )).delete(synchronize_session=False)
    # Удаляем все текущие вопросы
    db.query(models.Question).filter(models.Question.poll_id == poll_id).delete()

    create_question(db=db, questions=poll.question, poll_id=db_poll.id)
    db.commit()

    db.refresh(db_poll)
    return db_poll


# update poll status
async def update_poll_status(db: Session,
                             poll_id: int,
                             db_mongo: AsyncIOMotorCollection,
                             payload_status: schemas.PollStatusUpdate,
                             user_id: int):
    """
    Обновление статуса опроса


    :param db:
    :param poll_id:
    :param db_mongo:
    :param payload_status:
    :param user_id:
    :return: db_poll
    """
    db_poll = db.query(models.Poll).filter(models.Poll.id == poll_id).filter(models.Poll.user_id == user_id) \
        .options(joinedload(models.Poll.question)).first()
    if not db_poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    # otherwise update poll
    new_status = payload_status.poll_status
    if new_status == StatusPoll.PUBLISHED:
        # При обновлении проверяем есть ли хотя бы один вопрос и один вариант ответа в опросе
        if not db_poll.question:
            raise HTTPException(status_code=400, detail="At least one question is required to publish the poll")
        for question in db_poll.question:
            if not question.choice:
                raise HTTPException(status_code=400,
                                    detail="Each question must have at least one choice to publish the poll")
        db_poll.poll_status = PollStatus.PUBLISHED
        db_poll.poll_url = f"/poll/{db_poll.uuid}"
        db.commit()
    elif new_status == StatusPoll.DRAFT:
        # Сброс URL, если опрос переводится в черновик, завершается вручную удаляем все сессии
        db_poll.poll_url = None
        db_poll.poll_status = PollStatus.DRAFT
        await db_mongo.delete_many({"poll_uuid": str(db_poll.uuid)})
        db.query(models.Response).filter(models.Response.poll_id == poll_id).delete()
        db.commit()
    elif new_status == PollStatus.ENDED:
        # опрос завершен - удаляем все связанные сессии
        db_poll.poll_status = PollStatus.ENDED
        db_poll.poll_url = None
        await db_mongo.delete_many({"poll_uuid": str(db_poll.uuid)})
        db.commit()
    else:
        raise HTTPException(status_code=400, detail="Invalid poll status")

    db.refresh(db_poll)
    return db_poll


# query to delete poll by id
def delete_poll(db: Session, poll_id: int):
    """"
    Удаление опроса

    :param db: сессия БД
    :param poll_id: id опроса
    :return: удаленный опрос
    """
    db_poll = db.query(models.Poll).filter(models.Poll.id == poll_id).first()
    if not db_poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    db.delete(db_poll)
    db.commit()
    return db_poll


# query to delete poll by id and user_id
def delete_poll_by_user(db: Session, poll_id: int, user_id: int):
    """
    Удаление опроса

    :param db:
    :param poll_id:
    :param user_id:
    :return: db_poll
    """
    db_poll = db.query(models.Poll).filter(models.Poll.id == poll_id).filter(models.Poll.user_id == user_id).first()
    if not db_poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    db.delete(db_poll)
    db.commit()
    return db_poll


# service for uploading poll cover
def upload_poll_cover(db: Session, file: UploadFile, poll_id: int, user_id: int):
    # ckeck if file is an image
    mime_type, _ = guess_type(file.filename)
    if not mime_type or not mime_type.startswith("image"):
        raise HTTPException(status_code=400, detail="File must be an image")
    # check if the user has rights to change the poll
    db_poll = db.query(models.Poll).filter(models.Poll.id == poll_id).filter(models.Poll.user_id == user_id).first()
    if not db_poll:
        raise HTTPException(status_code=403, detail="You do not have rights to change this poll")
    # upload file
    file_name = f"{poll_id}_{file.filename}"
    path = f"{file_name}"
    try:
        with open(f"{settings.MEDIA_ROOT}/{file_name}", "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except IOError:
        raise HTTPException(status_code=500, detail="Could not upload file")
    db_poll.poll_cover = path
    db.add(db_poll)
    db.commit()
    return file_name


# QUESTIONS


# get all questions from poll
def get_all_poll_questions(db: Session, poll_id: int, user_id: int):
    """
    Получение всех вопросов опроса

    :param db: сессия БД
    :param poll_id: id опроса
    :param user_id: id пользователя
    :return: список вопросов
    """
    db_poll = db.query(models.Poll).filter(models.Poll.id == poll_id, models.Poll.user_id == user_id).first()
    if not db_poll:
        raise HTTPException(status_code=404, detail="Poll not found for the user")
    return db.query(models.Question).filter(models.Question.poll_id == poll_id).all()


# get all questions from poll by uuid
def get_all_poll_questions_by_uuid(db: Session, poll_uuid: UUID):
    """"
    Получение всех вопросов опроса по uuid

    :param db: сессия БД
    :param poll_uuid: UUID опроса
    :return список вопросов

    """
    db_poll = db.query(models.Poll).filter(models.Poll.uuid == poll_uuid).first()
    if not db_poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    return db.query(models.Question).filter(models.Question.poll_id == db_poll.id).all()


# Choices


# update question
def update_question(db: Session, question_id: int, question: schemas.UpdateQuestion):
    db_question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not db_question:
        raise HTTPException(status_code=404, detail="Question not found")
    # otherwise update question
    question_data = question.dict(exclude_none=True)
    for key, value in question_data.items():
        setattr(db_question, key, value)
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question


# RESPONSES

# utility common function for creating response in db
def create_response(db: Session,
                    db_question: models.Question,
                    answer_text=None,
                    answer_choice=None,
                    user_token=None):
    """Создание ответа на вопрос - общая функция для всех обработчиков


    :param db: сессия БД,
    :param db_question: модель вопроса,
    :param answer_text: текст ответа для вопроса с текстовым ответом,
    :param answer_choice: id варианта ответа может быть списков из нескольких элементов
    :param user_token: токен пользователя,
    """

    db_response = models.Response(
        poll_id=db_question.poll_id,
        question_id=db_question.id,
        answer_text=answer_text,
        answer_choice=answer_choice,
        user_token=user_token
    )
    db.add(db_response)
    db.commit()
    db.refresh(db_response)
    return db_response


# utility function for validate if a choice belongs to a question
def validate_choice(db: Session, question_id: int, choice_id: int):
    """
    Проверка принадлежности варианта ответа к вопросу

    :param db: сессия БД,
    :param question_id: id вопроса,
    :param choice_id: id варианта ответа,
    :return db_choice
    """
    db_choice = db.query(models.Choice).filter_by(id=choice_id, question_id=question_id).first()

    if not db_choice:
        raise HTTPException(status_code=404, detail="Invalid choice ID for this question")
    return db_choice


# create new response for using in endpoint!!!
async def create_new_response(db: Session,
                              poll_responses: schemas.CreatePollResponse,
                              db_mongo_session: SessionData,
                              db_mongo: AsyncIOMotorCollection = Depends(get_mongo_db),
                              uuid: UUID = None
                              ) -> List[models.Response]:
    """
    Функция для создания ответов на все вопросы в опросе - используется в эндпойнте


    :param db: сессия БД,
    :param poll_responses: схема со списком ответов на вопросы опроса,
    :param db_mongo_session: Сессия полученная из Mongo
    :param db_mongo db_mongo: Клиент MongoDB
    :param uuid: UUID опроса
    :return: список созданных ответов
    """
    # check if the poll exists
    db_poll = db.query(models.Poll).filter_by(uuid=uuid).first()

    #  Проверка на наличие опроса
    if not db_poll:
        raise HTTPException(status_code=404, detail="Poll not found for the user")
    #  Проверка на активность опроса - есть время начала и время окончания опроса
    if db_poll.is_ended():
        raise HTTPException(status_code=400, detail="The poll is ended!")

    # Проверка времени завершения сессии
    expires_at = db_mongo_session["expires_at"]
    if expires_at and expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Session expired")

    token = db_mongo_session["token"]
    logger.info(f'Token: {token}')
    response_objects = []
    # iterate over the responses and create response objects
    # TODO with a UUID check if already answered using anonymous token
    for single_response in poll_responses.responses:
        db_question = db.query(models.Question).filter(models.Question.id == single_response.question_id).first()
        if not db_question:
            raise HTTPException(status_code=404,
                                detail=f"Question with given ID  - {single_response.question_id} not found")
        # Check the question type and handle the response accordingly
        question_handler = question_handlers.get(db_question.type)
        if question_handler is None:
            raise HTTPException(status_code=500, detail="Invalid question type")
        db_response = question_handler(db, db_question, single_response, token)
        response_objects.append(db_response)

    # После сохранения всех ответов, проверяем, все ли пользователи ответили
    completed_sessions = await db_mongo.count_documents({"poll_uuid": str(uuid), "answered": True})
    # total_sessions = await db_mongo.count_documents({"poll_uuid": str(uuid)})
    if db_poll.max_participants is not None and completed_sessions == db_poll.max_participants - 1:
        db_poll.poll_status = PollStatus.ENDED
        db.commit()
    await db_mongo.update_one({"token": token}, {"$set": {"answered": True}})

    return response_objects


def handle_single_choice_response(db, db_question: models.Question, response_data: schemas.ResponsePayload, token: str):
    """
    Обработчик ответа на вопрос с одним вариантом ответа


    :param db: сессия БД,
    :param db_question: модель вопроса,
    :param response_data: общая схема для создания ответа на вопрос
    :param token: токен пользователя,
    :return create_response

    """

    # check that response data has only choice_id for single choice question
    if not (response_data.choice_id or response_data.choice_ids) or response_data.choice_text:
        raise HTTPException(status_code=400, detail="Invalid answer data for single choice question")
    validate_choice(db, db_question.id, response_data.choice_id)
    return create_response(db, db_question, answer_choice=[response_data.choice_id], user_token=token)


def handle_multiple_choice_response(db, db_question: models.Question, response_data: schemas.ResponsePayload, token: str):
    """
    Обработчик ответа на вопрос с несколькими вариантами ответа


    :param db: сессия БД,
    :param db_question: модель вопроса,
    :param response_data: общая схема для создания ответа на вопрос
    :return create_response
    """
    # check that response data has only choice_ids for multiple choice question
    if not (response_data.choice_id or response_data.choice_ids) or response_data.choice_text:
        raise HTTPException(status_code=400, detail="Invalid answer data for multiple choice question")
    for choice_id in response_data.choice_ids:
        validate_choice(db, db_question.id, choice_id)

    return create_response(db, db_question, answer_choice=response_data.choice_ids, user_token=token)


def handle_text_response(db, db_question: models.Question, response_data: schemas.ResponsePayload, token: str):
    """
    Обработчик ответа на вопрос с одним или несколькими текстовыми ответоми


    :param db: сессия БД,
    :param db_question: модель вопроса,
    :param response_data: схема для создания ответа на вопрос с текстовым ответом"""

    # check that response data has only answer_text for text question
    if not response_data.choice_text or response_data.choice_id or response_data.choice_ids:
        raise HTTPException(status_code=400, detail="Invalid answer data for text question")
    return create_response(db, db_question, answer_text=response_data.choice_text, user_token=token)


# Map question type to handler function
question_handlers = {
    "SINGLE ANSWER": handle_single_choice_response,
    "PLURAL ANSWER": handle_multiple_choice_response,
    "FREE ANSWER": handle_text_response,  # multiple text
    "FREE TEXT ANSWER": handle_text_response  # single text
}


# delete question from the user poll
def delete_question(db: Session, poll_id: int, question_id: int, user_id: int):
    """
    Удаление вопроса

    :param db: сессия БД,
    :param poll_id: id опроса,
    :param question_id: id вопроса,
    :param user_id: id пользователя,
    :return: удаленный вопрос
    """
    # check that question is belong to user
    db_poll = db.query(models.Poll).filter(models.Poll.id == poll_id).filter(models.Poll.user_id == user_id).first()
    if not db_poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    # check that question is belong to poll
    db_question = db.query(models.Question).filter(models.Question.id == question_id).filter(
        models.Question.poll_id == poll_id).first()
    if not db_question:
        raise HTTPException(status_code=404, detail="Question not found")
    db.delete(db_question)
    db.commit()
    return db_question


# get stats for all responses from poll
def get_poll_stats_responses(db: Session, poll_id: int, user_id: int):
    """
    Получение статистики по ответам на опрос

    :param db:
    :param poll_id:
    :param user_id:
    :return: responses
    """
    db_poll = (
        db.query(models.Poll)
        .options(
            joinedload(models.Poll.question).joinedload(models.Question.choice)
        )
        .filter(models.Poll.id == poll_id)
        .filter(models.Poll.user_id == user_id)
        .first()
    )
    if not db_poll:
        raise HTTPException(status_code=404, detail="Poll not found")

    # Проверка статуса опроса
    if db_poll.poll_status != PollStatus.ENDED:
        raise HTTPException(status_code=400, detail="Poll results are not available until the poll has ended")

    responses = []
    stats = []

    # Сбор статистики по ответам на вопросы и сами ответы
    for question in db_poll.question:
        # Получаем все ответы на текущий вопрос
        question_responses = question.response
        # Собираем статистику по ответам
        answer_stats = {}
        # Собираем индивидуальные ответы пользователей
        for response in question_responses:
            # Структура для хранения индивидуального ответа
            user_response = {
                "questionId": question.id,
                "questionText": question.text,
                "answerType": question.type.value,
                "selectedOptionIds": response.answer_choice or [],
                "answerText": response.answer_text or "",
                "userToken": response.user_token
            }
            responses.append(user_response)

            # if response.answer_choice:
            #     # Если ответ представляет собой выбор
            #     for choice_id in response.answer_choice:
            #         # Получаем текст выбора из уже загруженных данных
            #         choice_text = next((choice.text for choice in question.choice if choice.id == choice_id),
            #                            "Неизвестный выбор")
            #         # user_response["selectedOptionIds"].append(choice_id)
            #         # Статистика ответов пользователя
            #         if choice_text not in answer_stats:
            #             answer_stats[choice_text] = 1
            #         else:
            #             answer_stats[choice_text] += 1
            # elif response.answer_text:
            #     # Если ответ представляет собой текст
            #     # user_response["answerText"] = response.answer_text
            #     # Статистика ответов пользователя
            #     if response.answer_text not in answer_stats:
            #         answer_stats[response.answer_text] = 1
            #     else:
            #         answer_stats[response.answer_text] += 1

            if question.type == "PLURAL ANSWER" or question.type == "SINGLE ANSWER":
                for choice_id in response.answer_choice:
                    choice_text = next((choice.text for choice in question.choice if choice.id == choice_id),
                                       "Неизвестный выбор")
                    answer_stats[choice_text] = answer_stats.get(choice_text, 0) + 1
            elif question.type == "FREE ANSWER" and response.answer_text:
                answer_stats[response.answer_text] = answer_stats.get(response.answer_text, 0) + 1

        stats.append(
            {
                "questionId": question.id,
                "questionText": question.text,
                "items": answer_stats
            }
        )
    return {
        "responses": responses,
        "stats": stats
    }

#
# async def get_all_poll_responses(db: Session, poll_id: int, user_id: int):
#     """
#     Получение всех ответов на опрос по его id
#
#     :param db: сессия БД,
#     :param poll_id: id опроса,
#     :param user_id: id пользователя,
#     :return: ответы на опрос
#     """
#
#     db_poll = (
#         db.query(models.Poll)
#         .options(
#             joinedload(models.Poll.question)
#         )
#         .filter(models.Poll.id == poll_id)
#         .filter(models.Poll.user_id == user_id)
#         .first()
#     )
#     if not db_poll:
#         raise HTTPException(status_code=404, detail="Poll not found")
#     # Проверка статуса опроса
#     if db_poll.poll_status != PollStatus.ENDED:
#         raise HTTPException(status_code=400, detail="Poll results are not available until the poll has ended")
#
#


async def create_user_session(db: Session, uuid: UUID,
                              db_mongo: AsyncIOMotorCollection,
                              fingerprint: schemas.FingerPrint):
    """ Создание пользовательской сессии в MongoDB


    :param db: Сессия PostgreSQL
    :param uuid UUID опроса
    :param db_mongo: Сессия MongoDB
    :param poll: Модель опроса полученного из БД
    :param fingerprint: ID из FingerprintJS
    """

    poll = get_poll_by_uuid(db=db, uuid=uuid)
    if not poll:
        raise HTTPException(status_code=404, detail="Published Poll not found")
    if poll.poll_status == PollStatus.ENDED:
        raise HTTPException(status_code=400, detail="This poll is closed and does not accept new participants.")
    # создаем токен используя uuid опроса и текущее время
    token_data = {"poll_uuid": str(poll.uuid)}
    token = create_anonymous_user_token(data=token_data)

    max_participants = poll.max_participants
    if max_participants is not None:
        current_participants = await db_mongo.count_documents({"poll_uuid": str(uuid)})
        if current_participants == max_participants:
            raise HTTPException(status_code=400, detail="Maximum participants reached for this poll.")
        # elif current_participants == max_participants - 1:
        #     poll.poll_status = PollStatus.CLOSED
        #     db.commit()

    expires_at = None
    if poll.active_duration is not None:
        expires_at = datetime.utcnow() + timedelta(minutes=poll.active_duration)

    # создаем объект SessionData и сохраняем сессию опроса в MongoDB
    session_data = SessionData(
        token=token,
        fingerprint=fingerprint.fingerprint,
        poll_uuid=poll.uuid,
        expires_at=expires_at
    )
    result = await db_mongo.insert_one(document=session_data.to_dict())
    session_id = result.inserted_id
    return session_id, token


async def get_sessions_by_poll_uuid(db_mongo: AsyncIOMotorCollection, poll_uuid: UUID):
    """ Получение всех сессий опроса по poll_uuid из MongoDB


    :param db_mongo: Сессия MongoDB
    :param poll_uuid: UUID опроса
    :return: Список сессий опроса
    """

    sessions = await db_mongo.find({"poll_uuid": str(poll_uuid)}).to_list(length=None)
    return sessions
