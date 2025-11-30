# app/core/config.py

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # База
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://user:password@db:5432/newsdb"
    )

    # Redis (для кэша)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-change-me-in-prod!!!")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # неделя

    # S3 / MinIO
    S3_ENDPOINT: str = os.getenv("S3_ENDPOINT", "http://minio:9000")
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", "minioadmin")
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", "minioadmin")
    S3_BUCKET: str = "news-images"
    S3_PUBLIC_URL: str = os.getenv("S3_PUBLIC_URL", "http://localhost:9000/news-images")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()