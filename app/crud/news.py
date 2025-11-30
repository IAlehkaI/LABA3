# app/crud/news.py
# Здесь только «сырые» операции с базой — без кэша и бизнес-логики

from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from typing import List, Optional

from app.models.news import News as NewsModel
from app.schemas.news import NewsCreate, NewsUpdate


async def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[NewsModel]:
    """Все новости, отсортированные по дате (новые сверху)"""
    return (
        db.query(NewsModel)
        .order_by(desc(NewsModel.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )


async def get_by_id(db: Session, news_id: int) -> Optional[NewsModel]:
    """Получаем одну новость по id"""
    return db.query(NewsModel).filter(NewsModel.id == news_id).first()


async def create(db: Session, news_in: NewsCreate) -> NewsModel:
    """Создаём новость в БД"""
    db_news = NewsModel(**news_in.model_dump(exclude_unset=True))
    db.add(db_news)
    db.commit()
    db.refresh(db_news)
    return db_news


async def update(db: Session, news_id: int, news_in: NewsUpdate) -> Optional[NewsModel]:
    """Обновляем существующую новость"""
    db_news = db.query(NewsModel).filter(NewsModel.id == news_id).first()
    if not db_news:
        return None

    update_data = news_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_news, key, value)

    db.commit()
    db.refresh(db_news)
    return db_news


async def delete(db: Session, news_id: int) -> bool:
    """Удаляем новость"""
    db_news = db.query(NewsModel).filter(NewsModel.id == news_id).first()
    if not db_news:
        return False

    db.delete(db_news)
    db.commit()
    return True


async def search(db: Session, query: str) -> List[NewsModel]:
    """Поиск по заголовку, автору, краткому содержанию и тексту"""
    search = f"%{query.lower()}%"
    return (
        db.query(NewsModel)
        .filter(
            or_(
                NewsModel.title.ilike(search),
                NewsModel.author.ilike(search),
                NewsModel.summary.ilike(search),
                NewsModel.content.ilike(search),
            )
        )
        .order_by(desc(NewsModel.created_at))
        .all()
    )