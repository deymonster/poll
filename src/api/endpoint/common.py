from starlette.background import BackgroundTasks

from api.utils.logger import PollLogger
from company.schemas import CompanyCreate, CompanyOut, AllStatistics

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, Query, UploadFile, File
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse, JSONResponse

from base.schemas import Message
from api.utils.db import get_db
from api.utils.security import get_current_user_with_roles, get_current_user, get_current_active_user
from company import service as company_service
from poll import service as poll_service
from user.models import User, UserRole
from company import schemas
from user.schemas import UserCreateByEmail
from user.service import crud_user

# Logging
logger = PollLogger(__name__)

router = APIRouter()


# endpoint for summary statistics
@router.get("/statistics",  response_model=AllStatistics)
def get_statistics(db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_active_user)):
    """"Get statistics

    :param db: database session
    :param current_user: current user
    :return: statistics
    """

    try:
        company_statistics = company_service.get_monthly_company(db, 2024)
        poll_statistics = poll_service.get_monthly_poll(db, 2024)
        user_statistics = crud_user.get_monthly_users(db, 2024)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Errors while getting statistics: " + str(e))
    return {
        "company": company_statistics,
        "poll": poll_statistics,
        "user": user_statistics
    }