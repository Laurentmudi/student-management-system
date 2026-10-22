import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _db_url():
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    return "mysql+pymysql://{u}:{p}@{h}:{port}/{n}?charset=utf8mb4".format(
        u=quote_plus(os.getenv("DB_USER", "root")),
        p=quote_plus(os.getenv("DB_PASSWORD", "")),
        h=os.getenv("DB_HOST", "127.0.0.1"),
        port=os.getenv("DB_PORT", "3306"),
        n=os.getenv("DB_NAME", "tucode_sms"),
    )


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-me-please-32b")
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 60 * 12  # 12 hours
    SQLALCHEMY_DATABASE_URI = _db_url()
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(BASE_DIR, "uploads"))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
    ENABLE_SCHEDULER = os.getenv("ENABLE_SCHEDULER", "1") == "1"
    REMINDER_HOUR = int(os.getenv("REMINDER_HOUR", "8"))
