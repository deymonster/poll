from api.utils.logger import PollLogger
from EventLog.schemas import LogEntry
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, Query, UploadFile, File
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse, JSONResponse

from api.utils.parser_log import parse_log_line
from base.schemas import Message
from api.utils.db import get_db
from api.utils.security import get_current_user_with_roles, get_current_user, get_current_active_user
from company import service
from company.service import get_company_by_inn
from user.models import User, UserRole
from core.config import LOG_FILE_PATH




# Logging
logger = PollLogger(__name__)

router = APIRouter()


# endpoint to get all logs
@router.get("/logs", description='Endpoint to get all logs', response_model=List[LogEntry])
def read_log_file(db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_active_user)):
    """Endpoint to get all logs from file
    :param db: Session
    :param current_user: User with role superadmin
    :return: List of logs"""
    get_current_user_with_roles(current_user, required_roles=[UserRole.SUPERADMIN])
    log_entries = []
    log_file_path = "logs/all_logs.log"
    try:
        with open(log_file_path, 'r') as file:
            for line in file:
                log_entry = parse_log_line(line.strip())
                if log_entry:
                    log_entries.append(log_entry)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Errors while getting logs: " + str(e))
    return log_entries

