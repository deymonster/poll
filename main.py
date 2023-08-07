from pathlib import Path

from fastapi import FastAPI, Response, Request
import uvicorn
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse
from starlette.status import HTTP_401_UNAUTHORIZED

from src.api import routers
from db.session import SessionLocal, engine
from starlette.middleware.sessions import SessionMiddleware

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from src.api.utils.security import auth_middleware
import os

app = FastAPI(
    title="TestDesk",
    description="TestDesk API - это сервис для создания и прохождения опросов.",
    version="0.0.1",
)

origins = [
        "http://localhost:5173",# vue js
        "http://localhost:8000",
    ]


app.add_middleware(SessionMiddleware, secret_key="SomeRandomString",)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],)

# установка пути к папке с медиа файлами
media_path = os.path.abspath("media")

app.mount("/media", StaticFiles(directory=media_path), name="media")

app.mount("/static", StaticFiles(directory="static", html=True), name="static")



@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    response = Response("Internal server error", status_code=500)
    try:
        request.state.db = SessionLocal()
        response = await call_next(request)
    finally:
        request.state.db.close()
    return response

#app.middleware("http")(auth_middleware)
#app.middleware("http")(access_token_middleware)


app.include_router(routers.api_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)