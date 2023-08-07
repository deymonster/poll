import shutil

from fastapi import HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session, joinedload

from core.local_config import settings
from . import models, schemas
from typing import List
from base.service import CRUDBase
from mimetypes import guess_type

from uuid import UUID


class CRUDPoll(CRUDBase[schemas.Poll, schemas.CreatePoll, schemas.UpdatePoll]):
    # create new poll with questions

    def create_new_poll(self, db: Session, *, poll: schemas.CreatePoll, user_id: int):
        print(poll)
        with db.begin_nested():
            db_poll = models.Poll(**poll.dict(exclude={'questions'}), user_id=user_id)
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
    db_poll = models.Poll(**poll.dict(exclude={'questions'}), user_id=user_id)
    db.add(db_poll)
    db.commit()
    db.refresh(db_poll)
    create_question(db=db, questions=poll.question, poll_id=db_poll.id)
    return db_poll


# create new poll with title and description only
def create_new_simple_poll(db: Session, poll: schemas.CreateSimplePoll, user_id: int):
    db_poll = models.Poll(**poll.dict(), user_id=user_id)
    db.add(db_poll)
    db.commit()
    db.refresh(db_poll)
    return db_poll


# get all user polls
def get_all_user_poll(db: Session, user_id: int):
    return db.query(models.Poll).filter(models.Poll.user_id == user_id).all()


# get user polls paginated with sort by and search
def get_user_poll_paginated(db: Session, user_id: int, sort_by: str, page: int = 1, page_size: int = 20, query: str = None):
    query = query.lower() if query else None
    if sort_by == 'created_at_asc':
        order_by = models.Poll.created_at.asc()
    elif sort_by == 'created_at_desc':
        order_by = models.Poll.created_at.desc()
    elif sort_by == 'title':
        order_by = models.Poll.title.asc()
    else:
        order_by = models.Poll.created_at.desc() # default sort by created_at desc
    if query:
        polls = db.query(models.Poll).filter(models.Poll.user_id == user_id, models.Poll.title.contains(query)).order_by(order_by)
    else:
        polls = db.query(models.Poll).filter(models.Poll.user_id == user_id).order_by(order_by)
    polls = polls.offset((page - 1) * page_size).limit(page_size).all()
    total_polls = db.query(models.Poll).filter(models.Poll.user_id == user_id).count()
    print(f"Total polls {total_polls}")
    return polls, total_polls


# get all active user polls
def get_active_user_poll(db: Session, user_id: int):
    return db.query(models.Poll).filter(models.Poll.user_id == user_id, models.Poll.is_active == True).all()


# get single poll with questions and choices
def get_single_poll(db: Session, poll_id: int, user_id: int):
    return db.query(models.Poll).options(joinedload(models.Poll.question).joinedload(models.Question.choice)).\
        filter(models.Poll.id == poll_id).filter(models.Poll.user_id == user_id).first()


# get single poll with list of responses
def get_single_poll_with_response(db: Session, poll_id: int, user_id: int):
    return db.query(models.Response).filter(models.Poll.id == poll_id).all()


# get single poll with count of questions
def get_poll_detail(db: Session, poll_id: int, user_id: int):
    poll = db.query(models.Poll).filter(models.Poll.id == poll_id).filter(models.Poll.user_id == user_id).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    poll_data = {"created_at": poll.created_at,
                 "title": poll.title,
                 "description": poll.description,
                 "poll_cover": poll.poll_cover,
                 "is_active": poll.is_active,
                 "poll_url": poll.poll_url,
                 "user_id": user_id,
                 "question_count": db.query(models.Question).filter(models.Question.poll_id == poll_id).count()}
    print(poll_data)
    return poll_data


def get_poll_questions_paginated(db: Session, poll_uuid: UUID, page: int = 1, page_size: int = 1):
    # Get the poll with given uuid
    poll = db.query(models.Poll).filter(models.Poll.uuid == poll_uuid).first()

    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")

    questions = db.query(models.Question).options(joinedload(models.Question.choice))\
        .filter(models.Question.poll_id == poll.id)\
        .order_by(models.Question.id)
    questions = questions.offset((page - 1) * page_size).limit(page_size).all()
    total_questions = db.query(models.Question).filter(models.Question.poll_id == poll.id).count()
    print(f"Total questions {total_questions}")
    return questions, total_questions


# add question to poll
def create_poll_question(db: Session, question: schemas.QuestionCreate, poll_uuid: UUID):
    # Get the poll with given uuid
    poll = db.query(models.Poll).filter(models.Poll.uuid == poll_uuid).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    # otherwise create question
    #import pdb; pdb.set_trace()
    db_question = models.Question(**question.dict(), poll_id=poll.id)
    # add question to db
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question


# add choice to question
def create_question_choice(db: Session, choice: schemas.ChoiceCreate, question_id: int):
    # Get the question with given id
    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    # otherwise create choice
    db_choice = models.Choice(**choice.dict(), question_id=question.id)
    # add choice to db
    db.add(db_choice)
    db.commit()
    db.refresh(db_choice)
    return db_choice

# update poll
def update_poll(db: Session, poll_id: int, poll: schemas.UpdatePoll, user_id: int):
    db_poll = db.query(models.Poll).filter(models.Poll.id == poll_id).filter(models.Poll.user_id == user_id).first()
    if not db_poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    # otherwise update poll
    poll_data = poll.dict(exclude_unset=True)
    if poll.poll_cover is None:
        poll_data['poll_cover'] = None

    if poll.is_active:
        poll_data['poll_url'] = f"{settings.VUE_APP_BASE_URL}/poll/{db_poll.uuid}"
    else:
        poll_data['poll_url'] = None

    for key, value in poll_data.items():
        setattr(db_poll, key, value)
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

# add new question to poll
def create_new_question(db: Session, question: schemas.Question, poll_id: int):
    db_question = models.Question(**question.dict(), poll_id=poll_id)
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question


# get all questions from poll
def get_all_poll_questions(db: Session, poll_id: int):
    return db.query(models.Question).filter(models.Question.poll_id == poll_id).all()



# get all choices from question
def get_all_choices_from_question(db: Session, question_id: int):
    return db.query(models.Choice).filter(models.Choice.question_id == question_id).all()


# create list questions with nested choices - for creating poll
def create_question(db: Session, questions: List[schemas.Question], poll_id: int) -> List[models.Question]:
    db_questions = []
    for question in questions:
        db_question = models.Question(**question.dict(exclude={'choices'}), poll_id=poll_id)
        db.add(db_question)
        db.flush()
        db.refresh(db_question)
        db_choices = [models.Choice(**choice.dict(), question_id=db_question.id) for choice in question.choices]
        db.add_all(db_choices)
        db_questions.append(db_question)
    db.commit()


# get single question with choices
def get_single_question(db: Session, question_id: int):
    return db.query(models.Question).options(joinedload(models.Question.choice)).filter(models.Question.id ==
                                                                                         question_id).first()





# #create new poll
# def create_new_poll(db: Session, poll: schemas.CreatePoll, user_id: int):
#     db_poll = models.Poll(**poll.dict(exclude={'questions'}), user_id=user_id)
#     db.add(db_poll)
#     db.commit()
#     db.refresh(db_poll)
#     create_question(db=db, questions=poll.question, poll_id=db_poll.id)
#     return db_poll





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

# create new response
def create_new_response(db: Session, response_data: schemas.CreateSingleResponse, poll_id: int, question_id: int):
    print(response_data)
    # check if the poll exists
    db_poll = db.query(models.Poll).filter(models.Poll.id == poll_id).first()
    if not db_poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    # check if the question exists
    db_question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not db_question:
        raise HTTPException(status_code=404, detail="Question not found")
    # TODO with a UUID check if already answered using anonymous token
    # Check the question type and handle the response accordingly
    print({db_question.type})
    question_handler = question_handlers.get(db_question.type)
    if question_handler is None:
        raise HTTPException(status_code=500, detail="Invalid question type")
    db_response = question_handler(db, db_question, response_data.response)
    return db_response


def handle_single_choice_response(db, db_question: models.Question, response_data: schemas.SingleChoiceResponse):
    # single choice should have only one answer
    #if not response_data.choice_id or len(response_data.choice_id) != 1:
    print(response_data.choice_id)
    if not response_data.choice_id:
        raise HTTPException(status_code=400, detail="Invalid answer data for single choice question")
    # check if the choice belongs to the correct question
    choice_id = response_data.choice_id
    db_choice = db.query(models.Choice).filter_by(id=choice_id, question_id=db_question.id).first()
    if not db_choice:
        raise HTTPException(status_code=404, detail="Invalid choice ID for this question")
    # create a new response
    db_response = models.Response(poll_id=db_question.poll_id, question_id=db_question.id, answer_choice=choice_id)
    db.add(db_response)
    db.commit()
    db.refresh(db_response)
    return db_response


def handle_multiple_choice_response(db, question: models.Question, response_data: schemas.MultipleChoiceResponse):
    # validate the choice ids
    for choice_id in response_data.choice_ids:
        db_choice = db.query(models.Choice).filter_by(id=choice_id, question_id=question.id).first()
        if not db_choice:
            raise HTTPException(status_code=404, detail="Invalid choice ID for this question")
    # create a new response
    db_response = models.Response(poll_id=question.poll_id, question_id=question.id,
                                  answer_choice=response_data.choice_ids)
    db.add(db_response)
    db.commit()
    db.refresh(db_response)
    return db_response


def handle_free_answer_response(db, question: models.Question, response_data: schemas.MultipleTextResponse):
    db_response = models.Response(poll_id=question.poll_id, question_id=question.id,
                                  answer_text=response_data.answer_text)
    db.add(db_response)
    db.commit()
    db.refresh(db_response)
    return db_response


def handle_free_text_response(db, question: models.Question, response_data: schemas.SingleTextResponse):
    db_response = models.Response(poll_id=question.poll_id, question_id=question.id,
                                  answer_text=response_data.answer_text)
    db.add(db_response)
    db.commit()
    db.refresh(db_response)
    return db_response


# Map question type to handler function
question_handlers = {
    "SINGLE ANSWER": handle_single_choice_response,
    "PLURAL ANSWER": handle_multiple_choice_response,
    "FREE ANSWER": handle_free_answer_response, # multiple text
    "FREE TEXT ANSWER": handle_free_text_response # single text
}















