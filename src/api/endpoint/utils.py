from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic.networks import EmailStr
from starlette.status import HTTP_403_FORBIDDEN

from api.utils.security import get_current_active_superuser
from base.schemas import Msg
from user.schemas import User
from user.models import User as DBUser
from utils import send_test_email


router = APIRouter()


@router.post("/test-email/", response_model=Msg, status_code=201)
def test_email(
    email_to: EmailStr,
    current_user: DBUser = Depends(get_current_active_superuser),
):
    """
    Test emails.
    """
    send_test_email(email_to=email_to)
    return {"msg": "Test email sent"}


