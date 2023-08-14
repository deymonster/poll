from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, Query, UploadFile, File
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse, JSONResponse

from poll.schemas import QuestionPage, Question
from api.utils.security import get_current_user, get_current_active_user
from api.utils.db import get_db
from poll import schemas, service
from poll.service import crud_poll
from user.models import User
from user.schemas import UserBase

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import locale

from uuid import UUID

router = APIRouter()

current_dir = os.path.dirname(os.path.realpath(__file__))
# templates_dir = os.path.join(current_dir, '..', '..', 'templates')
templates = Jinja2Templates(directory='templates')



@router.post("/create2", response_model=schemas.Poll, deprecated=True)
def create_poll2(
        *,
        db: Session = Depends(get_db),
        poll_in: schemas.Poll,
        user: User = Depends(get_current_user),
):
    """
    Create new poll by user using CRUD base
    :param poll_in:
    :param db:
    :param user:
    :return:
    """
    print(poll_in)
    crud_poll.create_new_poll(db=db, poll=poll_in, user_id=user.id)
    return []


# POLL

# endpoint to get all user polls
@router.get("/user_polls", response_model=List[schemas.Poll])
def user_polls(db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    """
    Эндпоинт для получения списка опросов пользователя со статусом "Активен"
    :param db: Сессия базы данных
    :param user: Текущий пользователь со статусом "Активен"
    :return: Список опросов пользователя
    """
    polls = service.get_all_user_poll(db=db, user_id=user.id)
    return polls

# endpoint for adding new poll user for vue frontend
@router.post("/user_polls",  response_model=schemas.Poll)
def create_poll(poll_data: schemas.CreateSimplePoll, db: Session = Depends(get_db),
                user: User = Depends(get_current_active_user)):
    """ Эндпоинт для создания нового опроса c название и описанием пользователем
    :param poll_data: Данные опроса -  название и описание
    :param db: Сессия базы данных
    :param user: Текущий активнеы пользователь
    :return: Созданный опрос
    """
    poll = service.create_new_simple_poll(db=db, poll=poll_data, user_id=user.id)
    return poll


# endpoint for creating question of poll
@router.post("/user_polls/{poll_id}/questions/", response_model=schemas.Question)
def create_question(poll_id: int,
                    question: schemas.QuestionCreate,
                    db: Session = Depends(get_db),
                    user: User = Depends(get_current_active_user)):
    """ Эндпоинт для создания нового вопроса в опросе
    :param poll_id: Идентификатор опроса
    :param question: Данные вопроса согласно схеме QuestionCreate
    :param db: Сессия базы данных
    :param user: Текущий активный пользователь
    :return: Созданный вопрос

    Пример создания вопроса:
    {"type": "SINGLE ANSWER",
        "text": "Сколько вам лет?",
        "choices": [{"text": "Мне 10 лет"},
            {"text": "Мне 15 лет"},
            {"text": "Мне 20 лет"}]
    }

    """
    return service.create_single_question(db=db, poll_id=poll_id, question_data=question)





# Получение опроса со списками ответов
@router.get("/polls/{poll_id}/responses/", response_model=List[schemas.ListResponses])
def get_poll_responses(poll_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    return service.get_single_poll_with_response(db=db, poll_id=poll_id, user_id=user.id)


# endpoint for create new poll with  questions and nested choices
@router.post("/create_full/", response_model=schemas.Poll)
def create_poll(poll: schemas.Poll, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.create_new_poll(db=db, poll=poll, user_id=user.id)







# # QUESTION
#
#
# # endpoint for creating single question in poll
# @router.post("/polls/{poll_id}/questions/", response_model=schemas.Question)
# def create_question(poll_id: int, question: schemas.QuestionCreate, db: Session = Depends(get_db)):
#     return service.create_new_question(db=db, question=question, poll_id=poll_id)
#
#
# # endpoint for getting all questions from poll
# @router.get("/polls/{poll_id}/questions/", response_model=List[schemas.Question])
# def get_questions(poll_id: int, db: Session = Depends(get_db)):
#     return service.get_all_poll_questions(db=db, poll_id=poll_id)
#
#
# # endpoint for getting information about single question
# @router.get("/polls/{poll_id}/questions/{question_id}", response_model=schemas.SingleQuestion)
# def get_question(poll_id: int, question_id: int, db: Session = Depends(get_db)):
#     question = service.get_single_question(db=db, question_id=question_id)
#     if not question:
#         raise HTTPException(status_code=404, detail="Question not found")
#     return question
#
#
# # endpoint for getting all questions from poll
# @router.get("/polls/{poll_id}/questions/", response_model=List[schemas.Question])
# def get_active_questions(poll_id: int, db: Session = Depends(get_db)):
#     return service.get_all_poll_questions(db=db, poll_id=poll_id)
#
#
# # query for updating question
# @router.put("/polls/question/{question_id}", response_model=schemas.Question)
# def update_question(question_id: int, question: schemas.UpdateQuestion, db: Session = Depends(get_db)):
#     return service.update_question(db=db, question_id=question_id, question=question)
#
#
# # query get single question with choices
# @router.get("/polls/question/{question_id}", response_model=schemas.SingleQuestion)
# def get_question(question_id: int, db: Session = Depends(get_db)):
#     question = service.get_single_question(db=db, question_id=question_id)
#     if not question:
#         raise HTTPException(status_code=404, detail="Question not found")
#     return question
#
#
# # RESPONSE



# Получение детальной информации об опросе
@router.get("/polls/{poll_id}")
def get_poll(request: Request, poll_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    poll = service.get_single_poll(db=db, poll_id=poll_id, user_id=user.id)
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    return poll


#  endpoint for paginated user polls
@router.get("/polls", deprecated=True)
def polls(request: Request,
          page: int = 1,
          page_size: int = 20,
          db: Session = Depends(get_db),
          user: User = Depends(get_current_user)):
    """
    Polls page endpoint
    """
    user_id = user.id

    sort_by_options = {
        'created_at_asc': 'По возрастнию даты',
        'created_at_desc': 'По убыванию даты',
        'title': 'По названию',
    }
    sort_by = request.query_params.get('sort_by', 'created_at_desc')
    sort_by_label = sort_by_options.get(sort_by, 'Date Descending')
    polls, total_polls = service.get_user_poll_paginated(db=db, user_id=user_id, sort_by=sort_by, page=page,
                                                         page_size=page_size)

    return templates.TemplateResponse("polls.html",
                                      {"request": request,
                                       "polls": polls,
                                       # "month_names": month_names,
                                       "total_polls": total_polls,
                                       "page": page,
                                       "page_size": page_size,
                                       "sort_by": sort_by,
                                       "sort_by_label": sort_by_label})


# endpoint for searching polls
@router.get("/polls/search", deprecated=True)
def search_polls(request: Request,
                 query: str = Query(..., desription="Search query"),
                 page: int = Query(1, description="Page number"),
                 page_size: int = Query(20, description="Page size"),
                 sort_by: str = Query('created_at_desc', description="Sort by"),
                 db: Session = Depends(get_db)):
    """Endpoint for searching polls"""
    user_id = request.state.user.id
    polls, total_polls = service.get_user_poll_paginated(db=db,
                                                         user_id=user_id,
                                                         sort_by=sort_by,
                                                         page=page,
                                                         page_size=page_size,
                                                         query=query
                                                         )
    return templates.TemplateResponse("partials/poll_list.html",
                                      {"request": request,
                                       # "month_names": month_names,
                                       "polls": polls,
                                       "total_polls": total_polls, }
                                      )


# ednpoint for updating poll
@router.put("/polls/{poll_id}")
def update_poll(poll_id: int,
                poll_data: schemas.UpdatePoll,
                db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    """
    Update poll endpoint
    """
    print(poll_data)
    poll = service.update_poll(db=db, poll_id=poll_id, poll=poll_data, user_id=user.id)
    if poll:
        return {"success": True, "message": "Poll updated successfully", "poll": poll}
    else:
        raise HTTPException(status_code=500, detail="Erors while updating poll")


# endpoint for delete user poll by id and return polls list
@router.delete("/polls/{poll_id}", deprecated=True)
def delete_poll(request: Request, poll_id: int, db: Session = Depends(get_db)):
    """
    Delete poll endpoint
    """
    sort_by = request.query_params.get('sort_by', 'created_at_desc')
    print(sort_by)
    service.delete_poll_by_user(db=db, poll_id=poll_id, user_id=request.state.user.id)
    polls, total_polls = service.get_user_poll_paginated(db=db,
                                                         user_id=request.state.user.id,
                                                         sort_by=sort_by)
    return templates.TemplateResponse("partials/poll_list.html",
                                      {"request": request,
                                       # "month_names": month_names,
                                       "polls": polls,
                                       "total_polls": total_polls, }
                                      )


# endpoint for uploading image
@router.post("/polls/{poll_id}/upload_image")
async def upload_image(request: Request, poll_id: int, db: Session = Depends(get_db), image: UploadFile = File(...)):
    """
    Upload image endpoint
    """
    file_name = service.upload_poll_cover(db, file=image, poll_id=poll_id, user_id=request.state.user.id)
    return {"file_name": file_name}



# endpoint for adding new question to poll
@router.post("/polls/{poll_uuid}/questions", response_model=schemas.Question)
def add_question_to_poll(poll_uuid: UUID, question: schemas.QuestionCreate,
                         db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Add question to poll endpoint
    """
    # import pdb; pdb.set_trace()
    question = service.create_poll_question(db=db, question=question, poll_uuid=poll_uuid)
    return question


# Endpoint for displaying poll with one question and its choices per page
@router.get("/polls/{poll_uuid}/questions/{page}")
def get_poll_questions_paginated(poll_uuid: UUID, page: int = 1, db: Session = Depends(get_db)):
    """
    Get poll questions paginated endpoint
    """
    print(f'Poll uuid: {poll_uuid}')
    questions, total_questions = service.get_poll_questions_paginated(db=db, poll_uuid=poll_uuid, page=page)
    # import pdb; pdb.set_trace()
    return {"total_questions": total_questions, "questions": questions}


# endpoint for adding choice to question
@router.post("/polls/{poll_uuid}/questions/{question_id}/choices", response_model=schemas.Choice)
def add_choice_to_question(question_id: int, choice: schemas.ChoiceCreate, db: Session = Depends(get_db)):
    """
    Add choice to question endpoint
    """
    choice = service.create_question_choice(db=db, choice=choice, question_id=question_id)
    return choice
