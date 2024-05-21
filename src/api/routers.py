from fastapi import APIRouter


from api.endpoint import poll, login, users, utils, company, logevents, \
    common

api_router = APIRouter()
api_router.include_router(login.router, tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(utils.router, prefix="/utils", tags=["utils"])
api_router.include_router(poll.router, tags=["poll"])
api_router.include_router(company.router, tags=["companies"])
api_router.include_router(logevents.router, tags=["logs"])
api_router.include_router(common.router, tags=["statistics"])





