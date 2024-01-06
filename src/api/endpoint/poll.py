from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, Query, UploadFile, File
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import RedirectResponse, JSONResponse

from base.schemas import Message
from poll.schemas import QuestionPage, Question, SinglePoll
from api.utils.security import get_current_user, get_current_active_user
from api.utils.db import get_db
from poll import schemas, service
from poll.service import crud_poll
from user.models import User
from user.schemas import UserBase
from api.utils.logger import PollLogger

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import locale

from uuid import UUID

from api.utils.logger import PollLogger

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
        raise HTTPException(status_code=400, detail="Errors while getting user polls")


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
    ]

}

        ]

    """
    try:
        service.create_new_poll(db=db, poll=poll_data, user_id=user.id)
        #service.create_new_simple_poll(db=db, poll=poll_data, user_id=user.id)
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errors while updating poll - {e}")


# endpoint for changing poll status
@router.post("/user_polls/{poll_id}/status", response_model=Message)
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
    poll = service.update_poll_status(db=db, poll_id=poll_id, payload_status=payload_status, user_id=user.id)
    if poll:
        return JSONResponse(status_code=201, content={"message": "Poll updated successfully"})
    else:
        raise HTTPException(status_code=500, detail="Errors while updating poll status")


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


# QUESTIONS
# endpoint for getting all questions from poll
@router.get("/user_polls/{poll_id}/questions", response_model=List[schemas.Question], deprecated=True)
def get_poll_questions(poll_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    """ Эндпойнт для получения списка вопросов в опросе
    :param poll_id: Идентификатор опроса
    :param db: Сессия базы данных
    :param user: Текущий активный пользователь
    :return: Список вопросов в опросе"""
    questions = service.get_all_poll_questions(db=db, poll_id=poll_id, user_id=user.id)
    return questions


# endpoint for getting all questions from poll using uuid
@router.get("/user_polls/uuid/{poll_uuid}/questions", response_model=List[schemas.Question], deprecated=True)
def get_poll_questions_by_uuid(poll_uuid: UUID, db: Session = Depends(get_db)):
    """ Эндпойнт для получения списка вопросов в опросе
    :param poll_uuid: Идентификатор опроса
    :param db: Сессия базы данных
    :param user: Текущий активный пользователь
    :return: Список вопросов в опросе"""
    questions = service.get_all_poll_questions_by_uuid(db=db, poll_uuid=poll_uuid)
    return questions


# endpoint for creating question of poll
@router.post("/user_polls/{poll_id}/questions", response_model=schemas.Question, deprecated=True)
def create_question(question: schemas.QuestionCreate, poll_id: int, db: Session = Depends(get_db),
                    user: User = Depends(get_current_active_user)
                    ):
    """ Эндпоинт для создания нового вопроса в опросе c вариантами ответом
        :param poll_id: Идентификатор опроса
        :param question: Данные вопроса согласно схеме QuestionCreate
        :param db: Сессия базы данных
        :param user: Текущий активный пользователь
        :return: Созданный вопрос

        Пример создания вопроса:
        {"type": "SINGLE ANSWER",
            "text": "Сколько вам лет?",
            "choice": [{"text": "Мне 10 лет"},
                {"text": "Мне 15 лет"},
                {"text": "Мне 20 лет"}]
        }
        {"type": "PLURAL ANSWER",
            "text": "Выберите несколько утверждений, которые вам кажутся верными",
            "choice": [{"text": "Земля плоская"},
                {"text": "Земля круглая"},
                {"text": "Земля квадратная"}]
        }
        {"type": "FREE ANSWER",
            "text": "Укажите Ваше имя фамилию и вашу национальность",
            "choice": []
        }
        {"type": "FREE TEXT ANSWER",
            "text": "Ваше мнение по поводу плоской земли",
            "choice": []
        }
        """
    return service.create_single_question(db=db, poll_id=poll_id, user_id=user.id, question_data=question)


# endpoint for updating question of poll
@router.put("/user_polls/{poll_id}/questions/{question_id}", response_model=schemas.Question, deprecated=True)
def update_question(
        question_id: int,
        poll_id: int,
        question: schemas.QuestionUpdate,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_active_user)):
    """ Эндпоинт для обновления вопроса в опросе
    :param question_id: Идентификатор вопроса
    :param poll_id: Идентификатор опроса
    :param question: Данные вопроса согласно схеме QuestionUpdate
    :param db: Сессия базы данных
    :param user: Текущий активный пользователь
    :return: Обновленный вопрос"""
    service.update_single_question(db=db, poll_id=poll_id, question_id=question_id, question=question, user_id=user.id)
    return JSONResponse(status_code=201, content={"message": "Question updated successfully"})


# endpoint for deleting question from poll
@router.delete("/user_polls/{poll_id}/questions/{question_id}", response_model=Message, deprecated=True)
def delete_question(poll_id: int, question_id: int, db: Session = Depends(get_db),
                    user: User = Depends(get_current_active_user)):
    """ Эндпойнт для удаления вопроса в опросе
    :param poll_id: Идентификатор опроса
    :param question_id: Идентификатор вопроса
    :param db: Сессия базы данных
    :param user: Текущий активный пользователь
    :return message: Сообщение об  успешном удалении вопроса"""
    service.delete_question(db=db, poll_id=poll_id, question_id=question_id, user_id=user.id)
    return JSONResponse(status_code=204, content={"message": "Question was deleted"})


#
# #  endpoint for paginated user polls
# @router.get("/polls", deprecated=True)
# def polls(request: Request,
#           page: int = 1,
#           page_size: int = 20,
#           db: Session = Depends(get_db),
#           user: User = Depends(get_current_user)):
#     """
#     Polls page endpoint
#     """
#     user_id = user.id
#
#     sort_by_options = {
#         'created_at_asc': 'По возрастнию даты',
#         'created_at_desc': 'По убыванию даты',
#         'title': 'По названию',
#     }
#     sort_by = request.query_params.get('sort_by', 'created_at_desc')
#     sort_by_label = sort_by_options.get(sort_by, 'Date Descending')
#     polls, total_polls = service.get_user_poll_paginated(db=db, user_id=user_id, sort_by=sort_by, page=page,
#                                                          page_size=page_size)
#
#     return templates.TemplateResponse("polls.html",
#                                       {"request": request,
#                                        "polls": polls,
#                                        # "month_names": month_names,
#                                        "total_polls": total_polls,
#                                        "page": page,
#                                        "page_size": page_size,
#                                        "sort_by": sort_by,
#                                        "sort_by_label": sort_by_label})


# # endpoint for searching polls
# @router.get("/polls/search", deprecated=True)
# def search_polls(request: Request,
#                  query: str = Query(..., desription="Search query"),
#                  page: int = Query(1, description="Page number"),
#                  page_size: int = Query(20, description="Page size"),
#                  sort_by: str = Query('created_at_desc', description="Sort by"),
#                  db: Session = Depends(get_db)):
#     """Endpoint for searching polls"""
#     user_id = request.state.user.id
#     polls, total_polls = service.get_user_poll_paginated(db=db,
#                                                          user_id=user_id,
#                                                          sort_by=sort_by,
#                                                          page=page,
#                                                          page_size=page_size,
#                                                          query=query
#                                                          )
#     return templates.TemplateResponse("partials/poll_list.html",
#                                       {"request": request,
#                                        # "month_names": month_names,
#                                        "polls": polls,
#                                        "total_polls": total_polls, }
#                                       )


# # endpoint for delete user poll by id and return polls list
# @router.delete("/polls/{poll_id}", deprecated=True)
# def delete_poll(request: Request, poll_id: int, db: Session = Depends(get_db)):
#     """
#     Delete poll endpoint
#     """
#     sort_by = request.query_params.get('sort_by', 'created_at_desc')
#     service.delete_poll_by_user(db=db, poll_id=poll_id, user_id=request.state.user.id)
#     polls, total_polls = service.get_user_poll_paginated(db=db,
#                                                          user_id=request.state.user.id,
#                                                          sort_by=sort_by)
#     return templates.TemplateResponse("partials/poll_list.html",
#                                       {"request": request,
#                                        # "month_names": month_names,
#                                        "polls": polls,
#                                        "total_polls": total_polls, }
#                                       )


# # endpoint for uploading image
# @router.post("/polls/{poll_id}/upload_image")
# async def upload_image(request: Request, poll_id: int, db: Session = Depends(get_db), image: UploadFile = File(...)):
#     """
#     Upload image endpoint
#     """
#     file_name = service.upload_poll_cover(db, file=image, poll_id=poll_id, user_id=request.state.user.id)
#     return {"file_name": file_name}


#
# # endpoint for adding new question to poll
# @router.post("/polls/{poll_uuid}/questions", response_model=schemas.Question)
# def add_question_to_poll(poll_uuid: UUID, question: schemas.QuestionCreate,
#                          db: Session = Depends(get_db), user: User = Depends(get_current_user)):
#     """
#     Add question to poll endpoint
#     """
#     # import pdb; pdb.set_trace()
#     question = service.create_poll_question(db=db, question=question, poll_uuid=poll_uuid)
#     return question


# # Endpoint for displaying poll with one question and its choices per page
# @router.get("/polls/{poll_uuid}/questions/{page}")
# def get_poll_questions_paginated(poll_uuid: UUID, page: int = 1, db: Session = Depends(get_db)):
#     """
#     Get poll questions paginated endpoint
#     """
#     print(f'Poll uuid: {poll_uuid}')
#     questions, total_questions = service.get_poll_questions_paginated(db=db, poll_uuid=poll_uuid, page=page)
#     # import pdb; pdb.set_trace()
#     return {"total_questions": total_questions, "questions": questions}


# RESPONSES
# endpoint for creating response for all poll questions
@router.post("/user_polls/{poll_id}/responses", response_model=Message)
def create_poll_response(poll_id: int, poll_responses: schemas.CreatePollResponse, db: Session = Depends(get_db),
                         user: User = Depends(get_current_active_user)):
    """
    Эндпойнт для создания ответа на все вопросы опроса
    :param poll_id: Идентификатор опроса
    :param poll_responses: Схема для создания ответа на все вопросы опроса
    :param db: Сессия базы данных
    :param user: Текущий активный пользователь
    :return message: Сообщение об  успешном создании ответов на все вопросы опроса
    """
    #logger.info(f"Poll responses {poll_responses}")
    service.create_new_response(db=db, poll_responses=poll_responses, poll_id=poll_id, user_id=user.id)
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
