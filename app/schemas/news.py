# app/schemas/news.py
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List
from datetime import datetime


class NewsBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    image_url: Optional[HttpUrl] = None
    author: str = Field(..., min_length=2, max_length=100)
    summary: str = Field(..., min_length=10, max_length=500)
    content: str = Field(..., min_length=20)
    tags: Optional[List[str]] = []


class NewsCreate(NewsBase):
    pass


class NewsUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    image_url: Optional[HttpUrl] = None
    author: Optional[str] = Field(None, min_length=2, max_length=100)
    summary: Optional[str] = Field(None, min_length=10, max_length=500)
    content: Optional[str] = Field(None, min_length=20)
    tags: Optional[List[str]] = None


class NewsResponse(NewsBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    # Добавляем валидатор для конвертации строки в HttpUrl при чтении
    @classmethod
    def model_validate(cls, obj):
        if hasattr(obj, 'image_url') and isinstance(obj.image_url, str):
            obj.image_url = HttpUrl(obj.image_url) if obj.image_url else None
        return super().model_validate(obj)
