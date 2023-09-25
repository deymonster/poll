import os
import uvicorn
from fastapi import FastAPI, Response, Request
from starlette.middleware.cors import CORSMiddleware

from api import routers
from db.session import SessionLocal, db_session
from fastapi.staticfiles import StaticFiles
from api.utils.security import create_initial_user


app = FastAPI(
    title="TestDesk",
    description="TestDesk API - это сервис для создания и прохождения опросов.",
    version="0.0.1",
)

origins = [
    "http://localhost:5173",# vue js
    "http://localhost:4000",
    "http://localhost:8000",
    "http://localhost:9527"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.on_event("startup")
async def startup_event():
    create_initial_user(db=db_session())

app.include_router(routers.api_router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
