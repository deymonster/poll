from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    POSTGRES_PASSWORD: str
    POSTGRES_USER: str
    POSTGRES_DB: str
    DB_HOST: str = 'poll-db'
    DB_PORT: int = 5432

    JWT_PUBLIC_KEY: str
    JWT_PRIVATE_KEY: str
    REFRESH_TOKEN_EXPIRE_IN: int
    ACCESS_TOKEN_EXPIRE_IN: int
    JWT_ALGORITHM: str

    CLIENT_ORIGIN: str

    BASEDIR: str = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    MEDIA_ROOT: str = os.path.join(BASEDIR, 'media')
    VUE_APP_BASE_URL: str

    SERVER_HOST: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

PROJECT_NAME = "TestDesk"
#SERVER_HOST = 'http://127.0.0.1:5000'




# Email
SMTP_TLS = True
SMTP_PORT = None
SMTP_HOST = "SMTP_HOST"
SMTP_USER = "SMTP_USER"
SMTP_PASSWORD = "SMTP_PASSWORD"
EMAILS_FROM_EMAIL = "EMAILS_FROM_EMAIL"
EMAILS_FROM_NAME = "TestDesk Service"
EMAIL_RESET_TOKEN_EXPIRE_HOURS = 48
EMAIL_TEMPLATES_DIR = "/src/email-templates/build"
EMAILS_ENABLED = SMTP_HOST and SMTP_PORT and EMAILS_FROM_EMAIL

