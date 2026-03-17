from pydantic_settings import BaseSettings
from typing import Optional
from dotenv import load_dotenv
import os
load_dotenv()


class Settings(BaseSettings):
    APP_NAME: str = "Sync"
    DEBUG: bool = os.getenv('DEBUG', 'http://localhost:8001')
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'http://localhost:8001')
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    MONGODB_URL: str = os.getenv('MONGODB_URL', 'http://localhost:8001')
    DATABASE_NAME: str = "sync"

    CLOUDINARY_CLOUD_NAME: str = os.getenv('CLOUDINARY_CLOUD_NAME', 'http://localhost:8001')
    CLOUDINARY_API_KEY: str = os.getenv('CLOUDINARY_API_KEY', 'http://localhost:8001')
    CLOUDINARY_API_SECRET: str = os.getenv('CLOUDINARY_API_SECRET', 'http://localhost:8001')

    BACKEND_URL: str = "http://localhost:8000"
    ADMIN_URL: str = "http://localhost:5173"
    MOBILE_APP_URL: str = "sync://"

    WS_HEARTBEAT_INTERVAL: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
