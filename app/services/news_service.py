# app/services/news_service.py
# Бизнес-логика + кэширование. Один сервис — и для REST, и для gRPC, и для веб-форм

from typing import List, Optional
from sqlalchemy.orm import Session
import json

from app.crud.news import (
    get_all, get_by_id, create, update, delete, search
)
from app.schemas.news import NewsCreate, NewsUpdate, NewsResponse
from app.models.news import News as NewsModel
from app.core.redis import redis_client


class NewsService:
    # Кэш живёт 2 минуты для списка и поиска — достаточно для демо/лабы
    CACHE_TTL = 120

    async def _cache_key(self, prefix: str, *args) -> str:
        """Простая генерация ключа для Redis"""
        return f"news:{prefix}:{':'.join(map(str, args))}"

    def _serialize_news(self, news_list: List[NewsResponse]) -> str:
        """Сериализация списка новостей в JSON с поддержкой Pydantic v2"""
        return json.dumps(
            [item.model_dump(mode='json') for item in news_list],  # ← Pydantic v2
            ensure_ascii=False
        )

    async def get_all(self, db: Session) -> List[NewsResponse]:
        """Все новости с кэшем"""
        cache_key = await self._cache_key("all")
        cached = await redis_client.get(cache_key)
        if cached:
            raw_list = json.loads(cached)
            return [NewsResponse(**item) for item in raw_list]

        db_news = await get_all(db)
        result = [NewsResponse.model_validate(n) for n in db_news]  # ← Pydantic v2

        # Сохраняем в кэш
        await redis_client.setex(
            cache_key,
            self.CACHE_TTL,
            self._serialize_news(result)
        )
        return result

    async def get_by_id(self, db: Session, news_id: int) -> Optional[NewsResponse]:
        """Получаем одну новость — без кэша"""
        db_news = await get_by_id(db, news_id)
        return NewsResponse.model_validate(db_news) if db_news else None  # ← Pydantic v2

    async def create(self, db: Session, news_in: NewsCreate) -> NewsResponse:
        """Создаём новость и сразу чистим кэш списка"""
        db_news = await create(db, news_in)
        await self._invalidate_cache()
        return NewsResponse.model_validate(db_news)  # ← Pydantic v2

    async def update(self, db: Session, news_id: int, news_in: NewsUpdate) -> Optional[NewsResponse]:
        """Обновляем + инвалидируем кэш"""
        db_news = await update(db, news_id, news_in)
        if db_news:
            await self._invalidate_cache()
            return NewsResponse.model_validate(db_news)  # ← Pydantic v2
        return None

    async def delete(self, db: Session, news_id: int) -> bool:
        """Удаляем + чистим кэш"""
        success = await delete(db, news_id)
        if success:
            await self._invalidate_cache()
        return success

    async def search(self, db: Session, query: str) -> List[NewsResponse]:
        """Поиск с кэшем по запросу"""
        if not query.strip():
            return await self.get_all(db)

        cache_key = await self._cache_key("search", query.lower().strip())
        cached = await redis_client.get(cache_key)
        if cached:
            raw_list = json.loads(cached)
            return [NewsResponse(**item) for item in raw_list]

        db_news = await search(db, query)
        result = [NewsResponse.model_validate(n) for n in db_news]  # ← Pydantic v2

        await redis_client.setex(
            cache_key,
            self.CACHE_TTL,
            self._serialize_news(result)
        )
        return result

    async def _invalidate_cache(self):
        """Грубая, но надёжная очистка всех кэшей списка и поиска"""
        keys = await redis_client.keys("news:all*") + await redis_client.keys("news:search*")
        if keys:
            await redis_client.delete(*keys)


# Один глобальный экземпляр — удобно в DI
news_service = NewsService()
