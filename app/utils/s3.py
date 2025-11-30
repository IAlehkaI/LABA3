# app/utils/s3.py
# Загрузка изображений в MinIO (или любой S3-совместимый сервис)

import uuid
import boto3
from botocore.client import Config
from fastapi import HTTPException

from app.core.config import settings


# Один клиент на всё приложение
s3_client = boto3.client(
    "s3",
    endpoint_url=settings.S3_ENDPOINT,           # http://minio:9000
    aws_access_key_id=settings.S3_ACCESS_KEY,     # minioadmin
    aws_secret_access_key=settings.S3_SECRET_KEY, # minioadmin
    config=Config(signature_version="s3v4"),
    region_name="us-east-1"  # не важен для MinIO, но нужен boto3
)


async def upload_image_to_s3(file_content: bytes, original_filename: str) -> str:
    """
    Загружает картинку в бакет и возвращает публичную ссылку
    """
    try:
        # Генерируем уникальное имя, чтобы не было коллизий
        file_ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "jpg"
        unique_filename = f"{uuid.uuid4()}.{file_ext}"

        s3_client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=unique_filename,
            Body=file_content,
            ContentType=f"image/{file_ext if file_ext in ['jpg', 'jpeg', 'png', 'gif', 'webp'] else 'jpeg'}",
            ACL="public-read"  # делаем файл публичным
        )

        # Формируем прямую ссылку
        public_url = f"{settings.S3_PUBLIC_URL}/{unique_filename}"
        return public_url

    except Exception as e:
        # Если что-то пошло не так — падаем с понятной ошибкой
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки изображения: {str(e)}")