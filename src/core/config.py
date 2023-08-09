import os

from dotenv import load_dotenv

load_dotenv()


DB_HOST = os.getenv("DB_HOST", "pool-db")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
DB_PORT = os.getenv("DB_PORT", 5432)


API_V1_STR = "/api/v1"

# Secret key
SECRET_KEY = b"SECRET_KEY"
if not SECRET_KEY:
    SECRET_KEY = os.urandom(32)

# Token 60 minutes * 24 hours * 8 days = 8 days
ACCESS_TOKEN_EXPIRE_MINUTES = 15 * 24 * 8

# Token 60 minutes * 24 hours * 14 days = 14 days
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 14

# CORS
BACKEND_CORS_ORIGINS = [
    "http://localhost",
    "http://localhost:4200",
    "http://localhost:3000",
    "http://localhost:8080",
]

# Data Base
SQLALCHEMY_DATABASE_URI = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
)


PROJECT_NAME = "TestDesk"
SERVER_HOST = 'http://127.0.0.1:5000'

# Email
SMTP_TLS = True
SMTP_PORT = os.getenv("SMTP_PORT")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAILS_FROM_EMAIL = os.getenv("EMAILS_FROM_EMAIL")
EMAILS_FROM_NAME = "TestDesk Service"
EMAIL_RESET_TOKEN_EXPIRE_HOURS = 48
EMAIL_TEMPLATES_DIR = "email_templates/build"
EMAILS_ENABLED = bool(SMTP_HOST) and bool(SMTP_PORT) and bool(EMAILS_FROM_EMAIL)
