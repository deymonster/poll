from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, Query, UploadFile, File
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse, JSONResponse

from src.poll.schemas import QuestionPage, Question
from src.api.utils.security import get_current_user, get_current_active_user
from src.api.utils.db import get_db
from src.poll import schemas, service
from src.poll.service import crud_poll
from src.user.models import User
from src.user.schemas import UserBase

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import locale

from uuid import UUID



router = APIRouter()

current_dir = os.path.dirname(os.path.realpath(__file__))
# templates_dir = os.path.join(current_dir, '..', '..', 'templates')
templates = Jinja2Templates(directory='templates')

locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
month_names = [locale.nl_langinfo(locale.MON_1 + i) for i in range(12)]

@router.post("/create2", response_model=schemas.Poll)
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

# # Получение списка опросов
# @router.get("/polls/", response_model=List[schemas.Poll])
# def get_polls(db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
#     return service.get_all_user_poll(db=db, user_id=user.id)





# Получение опроса со списками ответов
@router.get("/polls/{poll_id}/responses/", response_model=List[schemas.ListResponses])
def get_poll_responses(poll_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    return service.get_single_poll_with_response(db=db, poll_id=poll_id, user_id=user.id)



# endpoint for create new poll with  questions and nested choices
@router.post("/create_full/", response_model=schemas.Poll)
def create_poll(poll: schemas.Poll, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.create_new_poll(db=db, poll=poll, user_id=user.id)


# endpoint for creating poll with title and description only
@router.post("/create/")
def create_poll(request: Request, poll: schemas.CreateSimplePoll, db: Session = Depends(get_db)):
    user_id = request.state.user.id
    service.create_new_simple_poll(db=db, poll=poll, user_id=user_id)
    return

# endpoint for adding in database new poll with createsimplepoll using data from form and return all user polls
@router.post("/create_from_form/")
async def create_poll(request: Request, db: Session = Depends(get_db)):
    user_id = request.state.user.id
    data = await request.form()
    poll = schemas.CreateSimplePoll(title=data['title'], description=data['description'])
    service.create_new_simple_poll(db=db, poll=poll, user_id=user_id)
    polls = service.get_all_user_poll(db=db, user_id=user_id)
    return templates.TemplateResponse("partials/poll_list.html", {"request": request,
                                                                  "month_names": month_names,
                                                                  "polls": polls})


# endpoint for adding new poll user for vue frontend
@router.post("/user_polls", tags=["poll_vue"], response_model=schemas.Poll)
def create_poll(request: schemas.CreateSimplePoll, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    poll = service.create_new_simple_poll(db=db, poll=request, user_id=user.id)
    return poll

#
#
# # endpoint for detail view of poll
# @router.get("/polls/{poll_id}/", response_model=schemas.PollDetail)
# def get_poll(poll_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
#     return service.get_poll_detail(db=db, poll_id=poll_id, user_id=user.id)
#
#
# # endpoint to get all polls from user
# @router.get("/api/polls/", response_model=List[schemas.ListPoll])
# def get_polls(db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
#     return service.get_all_user_poll(db=db, user_id=user.id)
#
#
# # endpoint to get all active polls from user
# @router.get("/polls/active/", response_model=List[schemas.Poll])
# def get_active_polls(db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
#     return service.get_active_user_poll(db=db, user_id=user.id)
#
#
# # endpoint for getting information about single poll
# @router.get("/polls2/{poll_id}", response_model=schemas.SinglePoll)
# def get_poll(poll_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
#     poll = service.get_single_poll(db=db, poll_id=poll_id, user_id=user.id)
#     if not poll:
#         raise HTTPException(status_code=404, detail="Poll not found")
#     return poll
#
#
# # # query for updating poll
# @router.put("/polls/{poll_id}", response_model=schemas.Poll)
# def update_poll(poll_id: int, poll: schemas.UpdatePoll, db: Session = Depends(get_db)):
#     return service.update_poll(db=db, poll_id=poll_id, poll=poll)
#
#
# # endpoint for deleting poll
# @router.delete("/polls/{poll_id}", response_model=schemas.Poll)
# def delete_poll(poll_id: int, db: Session = Depends(get_db)):
#     return service.delete_poll(db=db, poll_id=poll_id)
#
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
#
# # endpoint for creating response for question
# @router.post("/polls/{poll_id}/questions/{question_id}/response/")
# def create_response(poll_id: int,
#                     question_id: int,
#                     response_data: schemas.CreateSingleResponse,
#                     db: Session = Depends(get_db)
#                     ):
#     response = service.create_new_response(db=db, response_data=response_data, question_id=question_id, poll_id=poll_id)
#     if not response:
#         raise HTTPException(status_code=404, detail="Unable to create response")
#
#     return response
#
#
# # # endpoint for getting all responses for question
# # @router.get("/polls/{poll_id}/questions/{question_id}/response/")
# # def get_responses(poll_id: int, question_id: int, db: Session = Depends(get_db)):
#


# endpoint for login page
@router.get("/login")
def login(request: Request):
    access_token, refresh_token = get_token_from_cookie(request)
    if access_token is not None and refresh_token is not None:
        response = RedirectResponse(url='/user_polls', status_code=303)
        response.headers['Cache-Control'] = 'no-cache, must-revalidate'
        return response
    return templates.TemplateResponse("login.html", {"request": request})


# endpoint for login page v3
@router.get("/loginv3")
def login(request: Request):
    access_token, refresh_token = get_token_from_cookie(request)
    print(f'Token from loginv3: {access_token}')
    if access_token is not None and refresh_token is not None:
        # response = RedirectResponse(url='/polls', status_code=303)
        response = templates.TemplateResponse("polls.html", {"request": request})
        response.headers['Cache-Control'] = 'no-cache, must-revalidate'
        return response
    return templates.TemplateResponse("login-v3.html", {"request": request})




# endpoint for home page
@router.get("/home", response_class=HTMLResponse)
def home(request: Request, user: User = Depends(get_current_user)):
    """
    Home page endpoint
    """
    return templates.TemplateResponse("home.html", {"request": request})


# create test_login endpoint to redirect to polls page without depends
@router.get("/test_login", response_class=HTMLResponse)
def test(request: Request):
    """
    Test page endpoint
    """
    response = RedirectResponse(url='/polls', status_code=303)
    response.headers['Cache-Control'] = 'no-cache, must-revalidate'
    return response


# endpoint to get all user polls for vue
@router.get("/user_polls", tags=["poll_vue"])
def user_polls(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Polls page endpoint
    """
    polls = service.get_all_user_poll(db=db, user_id=user.id)
    return polls


# Получение детальной информации об опросе
@router.get("/polls/{poll_id}")
def get_poll(request: Request, poll_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    poll = service.get_single_poll(db=db, poll_id=poll_id, user_id=user.id)
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    return poll



#  endpoint for paginated user polls
@router.get("/polls")
def polls(request: Request,
          page: int =1,
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
    polls, total_polls = service.get_user_poll_paginated(db=db, user_id=user_id, sort_by=sort_by, page=page, page_size=page_size)

    return templates.TemplateResponse("polls.html",
                                      {"request": request,
                                       "polls": polls,
                                       "month_names": month_names,
                                       "total_polls": total_polls,
                                       "page": page,
                                       "page_size": page_size,
                                       "sort_by": sort_by,
                                       "sort_by_label": sort_by_label})


# endpoint for searching polls
@router.get("/polls/search")
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
                                         "month_names": month_names,
                                         "polls": polls,
                                         "total_polls": total_polls,}
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
@router.delete("/polls/{poll_id}")
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
                                         "month_names": month_names,
                                         "polls": polls,
                                         "total_polls": total_polls,}
                                        )


# endpoint for uploading image
@router.post("/polls/{poll_id}/upload_image")
async def upload_image(request: Request, poll_id: int, db: Session = Depends(get_db), image: UploadFile = File(...)):
    """
    Upload image endpoint
    """
    file_name = service.upload_poll_cover(db, file=image, poll_id=poll_id, user_id=request.state.user.id)
    return {"file_name": file_name}



# endpoint for displaying all polls
# @router.get("/user_polls/", response_class=HTMLResponse)
# def polls(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
#     """
#     Polls page endpoint
#     """
#     polls = service.get_all_user_poll(db=db, user_id=user.id)
#     return templates.TemplateResponse("poll2.html", {"request": request, "polls": polls})


# endpoint for adding new question to poll
@router.post("/polls/{poll_uuid}/questions", response_model=schemas.Question)
def add_question_to_poll(poll_uuid: UUID, question: schemas.QuestionCreate,
                         db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Add question to poll endpoint
    """
    #import pdb; pdb.set_trace()
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
    #import pdb; pdb.set_trace()
    return {"total_questions": total_questions, "questions": questions}


# endpoint for adding choice to question
@router.post("/polls/{poll_uuid}/questions/{question_id}/choices", response_model=schemas.Choice)
def add_choice_to_question(question_id: int, choice: schemas.ChoiceCreate, db: Session = Depends(get_db)):
    """
    Add choice to question endpoint
    """
    choice = service.create_question_choice(db=db, choice=choice, question_id=question_id)
    return choice


