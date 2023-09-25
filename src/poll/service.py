import shutil

from fastapi import HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session, joinedload

from core.local_config import settings
from . import models, schemas
from typing import List, Union
from base.service import CRUDBase
from mimetypes import guess_type
from typing import Optional

from uuid import UUID

from .models import PollStatus
from .schemas import QuestionType
from api.utils.logger import PollLogger

# Logging
logger = PollLogger(__name__).get_logger()


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

# create new poll with questions and choices
def create_new_poll(db: Session, poll: schemas.CreatePoll, user_id: int):
    db_poll = models.Poll(**poll.dict(exclude={"questions"}), user_id=user_id)
    db.add(db_poll)
    db.commit()
    db.refresh(db_poll)
    create_question(db=db, questions=poll.question, poll_id=db_poll.id)
    return db_poll


# create new poll with title and description only
def create_new_simple_poll(db: Session, poll: schemas.CreateSimplePoll, user_id: int):
    """ Создание нового опроса с название и описанием
    :param db: сессия БД
    :param poll: схема опроса
    :param user_id: id пользователя
    :return: созданный опрос"""
    db_poll = models.Poll(**poll.model_dump(), user_id=user_id)
    db.add(db_poll)
    db.commit()
    # change poll_url with uuid
    db_poll.poll_url = f"/poll/{db_poll.uuid}"
    db.commit()
    db.refresh(db_poll)
    return db_poll


# get all user polls
def get_all_user_poll(db: Session, user_id: int):
    return db.query(models.Poll).filter(models.Poll.user_id == user_id).all()


# get user polls paginated with sort by and search
def get_user_poll_paginated(
        db: Session, user_id: int, sort_by: str, page: int = 1, page_size: int = 20, query: str = None
):
    query = query.lower() if query else None
    if sort_by == "created_at_asc":
        order_by = models.Poll.created_at.asc()
    elif sort_by == "created_at_desc":
        order_by = models.Poll.created_at.desc()
    elif sort_by == "title":
        order_by = models.Poll.title.asc()
    else:
        order_by = models.Poll.created_at.desc()  # default sort by created_at desc
    if query:
        polls = (
            db.query(models.Poll)
            .filter(models.Poll.user_id == user_id, models.Poll.title.contains(query))
            .order_by(order_by)
        )
    else:
        polls = db.query(models.Poll).filter(models.Poll.user_id == user_id).order_by(order_by)
    polls = polls.offset((page - 1) * page_size).limit(page_size).all()
    total_polls = db.query(models.Poll).filter(models.Poll.user_id == user_id).count()
    logger.info(f"Total polls {total_polls}")
    return polls, total_polls


# get all active user polls
def get_active_user_poll(db: Session, user_id: int):
    return db.query(models.Poll).filter(models.Poll.user_id == user_id, models.Poll.is_active == True).all()


# get single poll with questions and choices
def get_single_poll(db: Session, poll_id: int, user_id: int):
    return (
        db.query(models.Poll)
        .options(joinedload(models.Poll.question)
        .joinedload(models.Question.choice))
        .filter(models.Poll.id == poll_id)
        .filter(models.Poll.user_id == user_id)
        .first())


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
    logger.info(poll_data)
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
    logger.info(f"Total questions {total_questions}")
    return questions, total_questions


# add question to poll
def create_poll_question(db: Session, question: schemas.QuestionCreate, poll_uuid: UUID):
    # Get the poll with given uuid
    poll = db.query(models.Poll).filter(models.Poll.uuid == poll_uuid).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    # otherwise create question
    # import pdb; pdb.set_trace()
    db_question = models.Question(**question.dict(), poll_id=poll.id)
    # add question to db
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question



# update poll
def update_poll(db: Session, poll_id: int, poll: schemas.UpdatePoll, user_id: int):
    db_poll = db.query(models.Poll).options(joinedload(models.Poll.question).joinedload(models.Question.choice))\
        .filter(models.Poll.id == poll_id).filter(models.Poll.user_id == user_id).first()
    #db.query(models.Poll)
        # .options(joinedload(models.Pll.question)
        # .joinedload(models.Question.choice))
        # .filter(models.Poll.id == poll_id)
        # .filter(models.Poll.user_id == user_id)
        # .first())
    if not db_poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    # otherwise update poll
    poll_data = poll.model_dump(exclude_unset=True)
    if poll.poll_cover is None:
        poll_data["poll_cover"] = None
    # if poll.poll_status == PollStatus.PUBLISHED:
    #     poll_data["poll_url"] = f"{settings.VUE_APP_BASE_URL}/poll/{db_poll.uuid}"
    # else:
    #     poll_data["poll_url"] = None
    for key, value in poll_data.items():
        setattr(db_poll, key, value)
    db.add(db_poll)
    db.commit()
    db.refresh(db_poll)
    return db_poll


# update poll status
def update_poll_status(db: Session, poll_id: int, payload_status: schemas.PollStatusUpdate, user_id: int):
    db_poll = db.query(models.Poll).filter(models.Poll.id == poll_id).filter(models.Poll.user_id == user_id).first()
    if not db_poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    # otherwise update poll
    if payload_status.poll_status:
        db_poll.poll_status = PollStatus.PUBLISHED
    else:
        db_poll.poll_status = PollStatus.DRAFT
    db.add(db_poll)
    db.commit()
    db.refresh(db_poll)
    return db_poll


# query to delete poll by id
def delete_poll(db: Session, poll_id: int):
    db_poll = db.query(models.Poll).filter(models.Poll.id == poll_id).first()
    if not db_poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    db.delete(db_poll)
    db.commit()
    return db_poll


# query to delete poll by id and user_id
def delete_poll_by_user(db: Session, poll_id: int, user_id: int):
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
    db_poll = db.query(models.Poll).filter(models.Poll.id == poll_id, models.Poll.user_id == user_id).first()
    if not db_poll:
        raise HTTPException(status_code=404, detail="Poll not found for the user")
    return db.query(models.Question).filter(models.Question.poll_id == poll_id).all()


# get all questions from poll by uuid
def get_all_poll_questions_by_uuid(db: Session, poll_uuid: UUID):
    db_poll = db.query(models.Poll).filter(models.Poll.uuid == poll_uuid).first()
    if not db_poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    return db.query(models.Question).filter(models.Question.poll_id == db_poll.id).all()


# get all choices from question
def get_all_choices_from_question(db: Session, question_id: int):
    return db.query(models.Choice).filter(models.Choice.question_id == question_id).all()


# create single question with  choices
def create_single_question(
        db: Session,
        poll_id: int,
        user_id: int,
        question_data: schemas.QuestionCreate,
) -> models.Question:
    """" Создание вопроса с вариантами ответа
    :param db: сессия БД
    :param poll_id: id опроса
    :param user_id: id пользователя
    :param question_data: схема вопроса
    """
    db_poll = db.query(models.Poll).filter(models.Poll.id == poll_id, models.Poll.user_id == user_id).first()
    if not db_poll:
        raise HTTPException(status_code=404, detail="Poll not found for the user")
    db_question = models.Question(**question_data.model_dump(exclude={"choice"}), poll_id=poll_id)
    db.add(db_question)
    db.flush()
    for choice_data in question_data.choice:
        db_choice = models.Choice(**choice_data.model_dump(), question_id=db_question.id)
        db.add(db_choice)
    db.commit()
    return db_question


# update single question
def update_single_question(db: Session, poll_id: int, question_id: int, question: schemas.QuestionUpdate, user_id: int):
    """Обновление вопроса с вариантами ответа
    :param db: сессия БД
    :param poll_id: id опроса
    :param question_id: id вопроса
    :param question: схема обновления
    :param user_id: id пользователя
    :return: обновленный вопрос
    """
    # check if the poll exists for the user
    db_poll = db.query(models.Poll).filter_by(id=poll_id, user_id=user_id).first()
    if not db_poll:
        raise HTTPException(status_code=404, detail="Poll not found for the user")
    db_question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not db_question:
        raise HTTPException(status_code=404, detail="Question not found")
    # otherwise update question
    for key, value in question.model_dump(exclude_unset=True).items():
        setattr(db_question, key, value)

    for choice in question.choice:
        db_choice = models.Choice(**choice.model_dump(), question_id=db_question.id)
        db.add(db_choice)
    db.commit()
    return db_question


# create list questions with nested choices - for creating poll
def create_question(db: Session, questions: List[schemas.Question], poll_id: int) -> List[models.Question]:
    db_questions = []
    for question in questions:
        db_question = models.Question(**question.dict(exclude={"choices"}), poll_id=poll_id)
        db.add(db_question)
        db.flush()
        db.refresh(db_question)
        db_choice = [models.Choice(**choice.dict(), question_id=db_question.id) for choice in question.choices]
        db.add_all(db_choice)
        db_questions.append(db_question)
    db.commit()


# get single question with choices
def get_single_question(db: Session, question_id: int):
    return (
        db.query(models.Question)
        .options(joinedload(models.Question.choice))
        .filter(models.Question.id == question_id)
        .first())

# Choices


# create new choice for question
def create_new_choice(db: Session, choice: schemas.ChoiceCreate, question_id: int):
    db_choice = models.Choice(**choice.model_dump(), question_id=question_id)
    db.add(db_choice)
    db.commit()
    db.refresh(db_choice)
    return db_choice


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
    """Проверка принадлежности варианта ответа к вопросу
    :param db: сессия БД,
    :param question_id: id вопроса,
    :param choice_id: id варианта ответа,
    """
    db_choice = db.query(models.Choice).filter_by(id=choice_id, question_id=question_id).first()

    if not db_choice:
        raise HTTPException(status_code=404, detail="Invalid choice ID for this question")
    return db_choice


# create new response for using in endpoint!!!
def create_new_response(db: Session, poll_responses: schemas.CreatePollResponse, poll_id: int, user_id: int) -> List[models.Response]:
    """Функция для создания ответов на все вопросы в опросе - используется в эндпойнте
    :param db: сессия БД,
    :param poll_responses: схема со списком ответов на вопросы опроса,
    :param poll_id: id опроса,
    :param user_id: id пользователя,
    :return: список созданных ответов
    """
    # check if the poll exists for the user
    db_poll = db.query(models.Poll).filter_by(id=poll_id, user_id=user_id).first()
    if not db_poll:
        raise HTTPException(status_code=404, detail="Poll not found for the user")
    response_objects = []
    # iterate over the responses and create response objects
    # TODO with a UUID check if already answered using anonymous token
    for single_response in poll_responses.responses:
        db_question = db.query(models.Question).filter(models.Question.id == single_response.question_id).first()
        if not db_question:
            raise HTTPException(status_code=404, detail=f"Question with given ID  - {single_response.question_id} not found")
        # Check the question type and handle the response accordingly
        question_handler = question_handlers.get(db_question.type)
        if question_handler is None:
            raise HTTPException(status_code=500, detail="Invalid question type")
        db_response = question_handler(db, db_question, single_response)
        response_objects.append(db_response)
    return response_objects


def handle_single_choice_response(db, db_question: models.Question, response_data: schemas.ResponsePayload):
    """ Обработчик ответа на вопрос с одним вариантом ответа
    :param db: сессия БД,
    :param db_question: модель вопроса,
    :param response_data: общая схема для создания ответа на вопрос,"""
    logger.info(response_data.choice_id)
    # check that response data has only choice_id for single choice question
    if not (response_data.choice_id or response_data.choice_ids) or response_data.choice_text or response_data.choice_texts:
        raise HTTPException(status_code=400, detail="Invalid answer data for single choice question")
    validate_choice(db, db_question.id, response_data.choice_id)
    return create_response(db, db_question, single_choice_id=response_data.choice_id)


def handle_multiple_choice_response(db, db_question: models.Question, response_data: schemas.ResponsePayload):
    """ Обработчик ответа на вопрос с несколькими вариантами ответа
    :param db: сессия БД,
    :param db_question: модель вопроса,
    :param response_data: общая схема для создания ответа на вопрос"""
    # check that response data has only choice_ids for multiple choice question
    if not (response_data.choice_id or response_data.choice_ids) or response_data.choice_text or response_data.choice_texts:
        raise HTTPException(status_code=400, detail="Invalid answer data for multiple choice question")
    for choice_id in response_data.choice_ids:
        validate_choice(db, db_question.id, choice_id)
    return create_response(db, db_question, multiple_choice_ids=response_data.choice_ids)


def handle_text_response(db, db_question: models.Question, response_data: schemas.ResponsePayload):
    """ Обработчик ответа на вопрос с одним или несколькими текстовыми ответоми
    :param db: сессия БД,
    :param db_question: модель вопроса,
    :param response_data: схема для создания ответа на вопрос с текстовым ответом"""
    # check that response data has only answer_text for text question
    if not (response_data.choice_texts or response_data.choice_text) or response_data.choice_id or response_data.choice_ids:
        raise HTTPException(status_code=400, detail="Invalid answer data for text question")
    return create_response(db, db_question, answer_text=response_data.choice_text or response_data.choice_texts)


# Map question type to handler function
question_handlers = {
    "SINGLE ANSWER": handle_single_choice_response,
    "PLURAL ANSWER": handle_multiple_choice_response,
    "FREE ANSWER": handle_text_response,  # multiple text
    "FREE TEXT ANSWER": handle_text_response  # single text
}


# delete question from the user poll
def delete_question(db: Session, poll_id: int, question_id: int, user_id: int):
    # check that question is belong to user
    db_poll = db.query(models.Poll).filter(models.Poll.id == poll_id).filter(models.Poll.user_id == user_id).first()
    if not db_poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    # check that question is belong to poll
    db_question = db.query(models.Question).filter(models.Question.id == question_id).filter(models.Question.poll_id == poll_id).first()
    if not db_question:
        raise HTTPException(status_code=404, detail="Question not found")
    db.delete(db_question)
    db.commit()
    return db_question


# get all responses from poll
def get_all_poll_responses(db: Session, poll_id: int, user_id: int):
    db_poll = db.query(models.Poll).filter(models.Poll.id == poll_id).filter(models.Poll.user_id == user_id).first()
    if not db_poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    return db.query(models.Response).filter(models.Response.poll_id == poll_id).all()
