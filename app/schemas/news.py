# app/schemas/news.py
# Pydantic-схемы — валидация входных и выходных данных

from pydantic import BaseModel, Field, HttpUrl, constr
from typing import List, Optional
from datetime import datetime


class NewsBase(BaseModel):
    title: constr(min_length=5, max_length=200) = Field(..., description="Заголовок новости")
    author: constr(min_length=2, max_length=100) = Field(..., description="Автор")
    summary: constr(min_length=50, max_length=500) = Field(..., description="Краткое содержание")
    content: constr(min_length=100) = Field(..., description="Полный текст новости")
    image_url: Optional[HttpUrl] = Field(None, description="Прямая ссылка на картинку (если есть)")
    tags: List[str] = Field(default_factory=list, description="Теги через запятую")


class NewsCreate(NewsBase):
    """Для создания новости — всё, что принимает клиент"""
    pass


class NewsUpdate(NewsBase):
    """Для обновления — все поля опциональные"""
    title: Optional[constr(min_length=5, max_length=200)] = None
    author: Optional[constr(min_length=2, max_length=100)] = None
    summary: Optional[constr(min_length=50, max_length=500)] = None
    content: Optional[constr(min_length=100)] = None
    image_url: Optional[HttpUrl] = None
    tags: Optional[List[str]] = None

    class Config:
        extra = "forbid"  # запрещаем лишние поля


class NewsResponse(NewsBase):
    """То, что отдаём наружу (в API и в шаблоны)"""
    id: int
    created_at: datetime
    tags: List[str] = []  # всегда список, даже если пустой

    class Config:
        from_attributes = True  # чтобы можно было делать NewsResponse.from_orm(db_news)
        json_encoders = {
            datetime: lambda v: v.isoformat()  # красивая дата в JSON
        }


# Удобная штука для веб-форм (когда не хочется делать отдельную схему)
class NewsInDB(NewsResponse):
    """Внутренняя схема — если нужно отдать что-то ещё (например, для отладки)"""
    pass