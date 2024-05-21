from starlette.background import BackgroundTasks

from api.utils.logger import PollLogger
from company.schemas import CompanyCreate, CompanyOut

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, Query, UploadFile, File
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse, JSONResponse

from base.schemas import Message
from api.utils.db import get_db
from api.utils.security import get_current_user_with_roles, get_current_user, get_current_active_user
from company import service
from company.service import get_company_by_inn
from user.models import User, UserRole
from company import schemas
from user.schemas import UserCreateByEmail
from user.service import crud_user

# Logging
logger = PollLogger(__name__)

router = APIRouter()


# COMPANIES


# endpoint to get all companies
@router.get("/companies", description='Endpoint to get all companies', response_model=List[CompanyOut])
def get_companies(db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_active_user)):
    """Endpoint to get all companies
    :param db: Session
    :param current_user: User with role superadmin
    :return: List of companies"""
    get_current_user_with_roles(current_user, required_roles=[UserRole.SUPERADMIN])
    try:
        companies = service.get_all_companies(db)
        logger.info(f"Companies - {companies[0].name}")
        return companies
    except Exception as e:
        raise HTTPException(status_code=400, detail="Errors while getting all companies: " + str(e))


# enpoint to create company
@router.post("/companies", description='Endpoint to create company')
def create_company(
        *,
        request: Request,
        data: schemas.CompanyCreate,
        db: Session = Depends(get_db),
        background_tasks: BackgroundTasks,
        current_user: User = Depends(get_current_active_user)
):
    """Endpoint to create company
    :param request: Request
    :param data: CompanyCreate
    :param db: Session
    :param background_tasks: BackgroundTasks
    :param current_user: User with role superadmin
    :return: JSONResponse with message and status code
    example of data:
    {"name": "МАОУ СОШ № 1",
    "full_name": "Муниципальное автономное общеобразовательное учреждение Средняя общеобразовательная школа № 1",
    "inn": "6658067728",
    "legal_address": "620028, Свердловская область, город Екатеринбург, Верх-Исетский б-р, стр. 23",
    "actual_address": "620028, Свердловская область, город Екатеринбург, Верх-Исетский б-р, стр. 23",
    "phone": "8(343)227-97-14",
    "director_name": "Махновецкий Алексей Витальевич",
    "admin_name": "Иванов Иван Иванович",
    "admin_email": "79228604051@yandex.ru",
    "licenses": 10000 }"""
    get_current_user_with_roles(current_user, required_roles=[UserRole.SUPERADMIN])
    try:
        if get_company_by_inn(db=db, inn=data.inn):
            raise HTTPException(
                status_code=409,
                detail="The company is exist with current INN",
            )

        company_id = service.create_new_company(db=db, data=data)

        obj_in = UserCreateByEmail(
            email=data.admin_email,
            full_name=data.admin_name,
            roles=[UserRole.ADMIN],
            company_id=company_id
        )
        if crud_user.get_by_email(db, email=data.admin_email):
            raise HTTPException(
                status_code=409,
                detail="The user with this username already exists in the system.",
            )

        crud_user.register_user(db_session=db,
                                request=request,
                                current_user=current_user,
                                obj_in=obj_in,
                                background_tasks=background_tasks)
        logger.info(event_type="Company creation",
                    obj=f"{data.full_name}",
                    subj=f"{data.full_name}",
                    action="Company created successfully",
                    additional_info=""
                    )
        return JSONResponse(status_code=201, content={"message": "Company created successfully"})
    except Exception as e:
        raise HTTPException(status_code=400, detail="Errors while creating company: " + str(e))


# endpoint to get company by id
@router.get("/companies/{company_id}", description='Endpoint to get company by id', response_model=CompanyOut)
def get_company_by_id(company_id: int, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_active_user)):
    """Endpoint to get company by id
    :param company_id: int
    :param db: Session
    :param current_user: User with role superadmin
    :return: CompanyBase"""
    get_current_user_with_roles(current_user, required_roles=[UserRole.SUPERADMIN])
    try:
        company = service.get_company_by_id(db=db, company_id=company_id)
        return company
    except Exception as e:
        raise HTTPException(status_code=400, detail="Errors while getting user polls with error: " + str(e))


# endpoint for updating company by id
@router.patch("/companies/{company_id}", description='Endpoint for updating company by id')
def update_company_by_id(company_id: int, data: schemas.CompanyUpdate, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_active_user)):
    """Endpoint for updating company by id
    :param company_id: int
    :param data: CompanyCreate
    :param db: Session
    :param current_user: User with role superadmin"""
    get_current_user_with_roles(current_user, required_roles=[UserRole.SUPERADMIN])
    try:
        service.update_company_by_id(db=db, company_id=company_id, data=data)
        return JSONResponse(status_code=200, content={"message": "Company updated successfully"})
    except Exception as e:
        raise HTTPException(status_code=400, detail="Errors while updating company with error: " + str(e))


# endpoint for deleting company by id
@router.delete("/companies/{company_id}", description='Endpoint for deleting company by id', deprecated=True)
def delete_company_by_id(company_id: int, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_active_user)):
    """Endpoint for deleting company by id
        :param company_id: int
        :param db: Session
        :param current_user: User with role superadmin"""
    get_current_user_with_roles(current_user, required_roles=[UserRole.SUPERADMIN])
    try:
        service.delete_company_by_id(db=db, company_id=company_id)
        return JSONResponse(status_code=200, content={"message": "Company deleted successfully"})
    except Exception as e:
        raise HTTPException(status_code=400, detail="Errors while deleting company with error: " + str(e))


# endpoint for change status of company and all its users
@router.patch("/companies/{company_id}/status", description="Endpoint for changing company status by id")
def change_company_status(company_id: int,
                          payload_status: schemas.CompanyStatusUpdate,
                          db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_active_user)):
    """Endpoint for changing company status
    :param company_id: Company ID
    :param payload_status: New status
    :param db: Session
    :param current_user: Current User

    """
    get_current_user_with_roles(current_user, required_roles=[UserRole.SUPERADMIN])
    try:
        service.update_company_status(db=db, company_id=company_id, status=status)
        return JSONResponse(status_code=200, content={"message": "Company status changed successfully"})
    except Exception as e:
        raise HTTPException(status_code=400, detail="Errors while deleting company with error: " + str(e))
