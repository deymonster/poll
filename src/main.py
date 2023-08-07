import os
import uvicorn
from fastapi import FastAPI, Response, Request
from starlette.middleware.cors import CORSMiddleware

from api import routers
from db.session import SessionLocal, engine
from fastapi.staticfiles import StaticFiles



app = FastAPI(
    title="TestDesk",
    description="TestDesk API - это сервис для создания и прохождения опросов.",
    version="0.0.1",
)

origins = [
    "http://localhost:5173",  # vue js
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"], )

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


app.include_router(routers.api_router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
