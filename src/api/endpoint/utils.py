from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic.networks import EmailStr
from starlette.status import HTTP_403_FORBIDDEN

from api.utils.security import get_current_user_with_role
from base.schemas import Msg
from user.schemas import User
from user.models import User as DBUser, UserRole
from utils import send_test_email


router = APIRouter()


@router.post("/test-email/", response_model=Msg, status_code=201)
def test_email(
    email_to: EmailStr,
    current_user: User = Depends(lambda: get_current_user_with_role(UserRole.SUPERADMIN)),
):
    """
    Test emails.
    """
    send_test_email(email_to=email_to)
    return {"msg": "Test email sent"}


