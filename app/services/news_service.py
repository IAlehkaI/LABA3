# app/services/news_service.py — С AWAIT
from sqlalchemy.orm import Session
from app.crud import news as crud
from app.schemas.news import NewsCreate, NewsUpdate
from typing import Optional, List
from app.models.news import News


class NewsService:
    """Сервисный слой для работы с новостями"""

    async def create(self, db: Session, news_in: NewsCreate) -> News:
        """Создание новости"""
        return await crud.create(db, news_in)

    async def get_all(self, db: Session) -> List[News]:
        """Получить все новости"""
        return await crud.get_all(db)

    async def get_by_id(self, db: Session, news_id: int) -> Optional[News]:
        """Получить новость по ID"""
        return await crud.get_by_id(db, news_id)

    async def search(self, db: Session, query: str) -> List[News]:
        """Поиск новостей"""
        return await crud.search(db, query)

    async def update(self, db: Session, news_id: int, news_in: NewsUpdate) -> bool:
        """Обновление новости"""
        return await crud.update(db, news_id, news_in)

    async def delete(self, db: Session, news_id: int) -> bool:
        """Удаление новости"""
        return await crud.delete(db, news_id)


news_service = NewsService()
