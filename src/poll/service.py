import shutil
import copy
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException, UploadFile, Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func

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
from .schemas import QuestionType, StatusPoll, UserSession
from api.utils.logger import PollLogger

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
        # token_data = {"poll_id": poll.id}
        # token = create_anonymous_user_token(data=token_data)
        # setattr(poll, 'token', token)
        return poll
    else:
        return None


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
    selected_fields = [models.Poll.id, models.Poll.created_at, models.Poll.title, models.Poll.description,
                       models.Poll.poll_cover, models.Poll.poll_status]
    query = db.query(*selected_fields).filter(models.Poll.user_id == user_id)

    if status:
        query = query.filter(models.Poll.poll_status == status)
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


def get_poll_questions_paginated(db: Session, poll_uuid: UUID, page: int = 1, page_size: int = 1):
    # Get the poll with given uuid
    poll = db.query(models.Poll).filter(models.Poll.uuid == poll_uuid).first()

    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")

    questions = (
        db.query(models.Question)
        .options(joinedload(models.Question.choice))
        .filter(models.Question.poll_id == poll.id)
        .order_by(models.Question.id))
    questions = questions.offset((page - 1) * page_size).limit(page_size).all()
    total_questions = db.query(models.Question).filter(models.Question.poll_id == poll.id).count()
    # logger.info(f"Total questions {total_questions}")
    return questions, total_questions


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

    # Вариант обновления перебором всех вопросов и вариантов
    # # обновляем вопросы и варианты ответов
    # for question in poll.question:
    #     db_question = next((q for q in db_poll.question if q.text == question.text), None)
    #     if db_question:
    #         print(f'Update Question - {db_question}')
    #         for attr, value in question.model_dump(exclude={"choice"}).items():
    #             setattr(db_question, attr, value)
    #
    #         for choice in question.choice:
    #             db_choice = next((c for c in db_question.choice if c.text == choice.text), None)
    #             if db_choice:
    #                 print(f'Update Choice - {db_choice}')
    #                 for attr, value in choice.model_dump().items():
    #                     setattr(db_choice, attr, value)
    #
    #             else:
    #                 print(f'Create new Choice - {choice}')
    #                 create_new_choice(db=db, choice=choice, question_id=db_question.id)
    #     else:
    #         print(f'Create new question - {question}')
    #         create_question(db, [question], db_poll.id)

    db.refresh(db_poll)
    return db_poll


# update poll status
def update_poll_status(db: Session, poll_id: int, payload_status: schemas.PollStatusUpdate, user_id: int):
    """
    Обновление статуса опроса

    :param db:
    :param poll_id:
    :param payload_status:
    :param user_id:
    :return: db_poll
    """
    db_poll = db.query(models.Poll).filter(models.Poll.id == poll_id).filter(models.Poll.user_id == user_id) \
        .options(joinedload(models.Poll.question)).first()
    if not db_poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    # otherwise update poll
    if payload_status.poll_status:
        if not db_poll.question:
            raise HTTPException(status_code=400, detail="At least one question is required to publish the poll")
        for question in db_poll.question:
            if not question.choice:
                raise HTTPException(status_code=400,
                                    detail="Each question must have at least one choice to publish the poll")
        db_poll.poll_status = PollStatus.PUBLISHED
        db_poll.poll_url = f"/poll/{db_poll.uuid}"

    else:
        db_poll.poll_status = PollStatus.DRAFT
        db_poll.poll_url = None
    db.add(db_poll)
    db.commit()
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
    # uplaod file
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
                    single_choice_id=None,
                    multiple_choice_ids=None,
                    answer_text=None):
    """Создание ответа на вопрос - общая функция для всех обработчиков
    :param db: сессия БД,
    :param poll_id: id опроса,
    :param db_question: модель вопроса,
    :param single_choice_id: id варианта ответа для вопроса с одним вариантом ответа,
    :param multiple_choice_ids: id вариантов ответа для вопроса с несколькими вариантами ответа,
    :param answer_text: текст ответа для вопроса с текстовым ответом,
    """

    db_response = models.Response(
        poll_id=db_question.poll_id,
        question_id=db_question.id,
        choice_id=single_choice_id,
        answer_choice=multiple_choice_ids,
        answer_text=answer_text
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
                              db_mongo_session: UserSession,
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
    if not db_poll.is_published():
        raise HTTPException(status_code=400, detail="The poll is not active anymore")
    # Проверка сессии на то, был ли уже ответ или нет
    if db_mongo_session.get("answered"):
        raise HTTPException(status_code=400, detail="The User Session has an answer")

        # Проверка времени завершения сессии
    expires_at = db_mongo_session.get("expires_at")
    if expires_at and expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Session expired")

    token = db_mongo_session.get("token")

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
        db_response = question_handler(db, db_question, single_response)
        response_objects.append(db_response)

    await db_mongo.update_one({"token": token}, {"$set": {"answered": True}})

    return response_objects


def handle_single_choice_response(db, db_question: models.Question, response_data: schemas.ResponsePayload):
    """
    Обработчик ответа на вопрос с одним вариантом ответа

    :param db: сессия БД,
    :param db_question: модель вопроса,
    :param response_data: общая схема для создания ответа на вопрос
    :return create_response
    """
    # logger.info(response_data.choice_id)
    # check that response data has only choice_id for single choice question
    if not (response_data.choice_id or response_data.choice_ids) or response_data.choice_text:
        raise HTTPException(status_code=400, detail="Invalid answer data for single choice question")
    validate_choice(db, db_question.id, response_data.choice_id)
    return create_response(db, db_question, single_choice_id=response_data.choice_id)


def handle_multiple_choice_response(db, db_question: models.Question, response_data: schemas.ResponsePayload):
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
    return create_response(db, db_question, multiple_choice_ids=response_data.choice_ids)


def handle_text_response(db, db_question: models.Question, response_data: schemas.ResponsePayload):
    """
    Обработчик ответа на вопрос с одним или несколькими текстовыми ответоми

    :param db: сессия БД,
    :param db_question: модель вопроса,
    :param response_data: схема для создания ответа на вопрос с текстовым ответом"""
    # check that response data has only answer_text for text question
    if not response_data.choice_text or response_data.choice_id or response_data.choice_ids:
        raise HTTPException(status_code=400, detail="Invalid answer data for text question")
    return create_response(db, db_question, answer_text=response_data.choice_text)


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


# get all responses from poll
def get_all_poll_responses(db: Session, poll_id: int, user_id: int):
    """
    Получение всех ответов на опрос
    :param db:
    :param poll_id:
    :param user_id:
    :return: responses
    """
    db_poll = db.query(models.Poll).filter(models.Poll.id == poll_id).filter(models.Poll.user_id == user_id).first()
    if not db_poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    return db.query(models.Response).filter(models.Response.poll_id == poll_id).all()


def get_poll_report(db: Session, poll_id: int):
    """
    Получение отчета по опросу
    :param db:
    :param poll_id:
    :param user_id:
    :return: responses
    """
    report = []
    questions = db.query(models.Question).filter(models.Question.poll_id == poll_id).all()
    for question in questions:
        total_responses = db.query(models.Response).filter(models.Response.question_id == question.id).count()
        if question.type == QuestionType.SINGLE:
            response_report = []
            choices = db.query(models.Choice).filter(models.Choice.question_id == question.id).all()
            for choice in choices:
                choice_count = db.query(models.Response).filter(models.Response.choice_id == choice.id).count()
                percentage = round((choice_count / total_responses) * 100, 2) if total_responses else 0
                response_report.append({"choice_id": choice.id,
                                        "count": choice_count,
                                        "percentage": percentage})
            report.append({"question_id": question.id, "responses": response_report})
        elif question.type == QuestionType.PLURAL:
            responses_report = []
            choices = db.query(models.Choice).filter(models.Choice.question_id == question.id).all()
            for choice in choices:
                choice_count = db.query(models.Response).filter(models.Response.choice_id == choice.id,
                                                                models.Response.question_id == question.id).count()
                percentage = round((choice_count / total_responses) * 100, 2) if total_responses else 0
                responses_report.append({"choice_id": choice.id,
                                         "count": choice_count,
                                         "percentage": percentage})
            report.append({"question_id": question.id, "responses": responses_report})
        elif question.type == QuestionType.FREE_TEXT:
            text_answers = db.query(models.Response.answer_text).filter(
                models.Response.question_id == question.id).all()
            report.append({"question_id": question.id,
                           "question_text": question.text,
                           "text_answer": [answer[0] for answer in text_answers if answer[0]]
                           })
        elif question.type == QuestionType.FREE:
            text_answers = db.query(models.Response.answer_text).filter(
                models.Response.question_id == question.id).all()
            report.append({"question_id": question.id,
                           "question_text": question.text,
                           "text_answers": [answer[0] for answer in text_answers if answer[0]]
                           })

    return report


async def create_user_session(db_mongo: AsyncIOMotorCollection, poll: models.Poll, fingerprint: schemas.FingerPrint):
    """ Создание пользовательской сессии в MongoDB


    :param db_mongo: Сессия MongoDB
    :param poll: Модель опроса полученного из БД
    :param fingerprint: ID из FingerprintJS
    """
    token_data = {"poll_uuid": str(poll.uuid)}
    token = create_anonymous_user_token(data=token_data)

    max_participants = poll.max_participants
    if max_participants is not None:
        current_participants = await db_mongo.count_documents({"poll_uuid": poll.uuid})
        if current_participants >= max_participants:
            raise HTTPException(status_code=400, detail="Maximum participants reached for this poll.")

    expires_at = None
    expired_status = False
    answered_status = False
    if poll.active_duration is not None:
        expires_at = datetime.utcnow() + timedelta(minutes=poll.active_duration)

    # Создаем и сохраняем сессию опроса в MongoDB
    session_data = {
        "token": token,
        "fingerprint": fingerprint.fingerprint,
        "poll_uuid": str(poll.uuid),
        "expires_at": expires_at,
        "expired": expired_status,
        "answered": answered_status
    }

    result = await db_mongo.insert_one(document=session_data)
    session_id = result.inserted_id
    return session_id, token
