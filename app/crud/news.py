# app/crud/news.py — АСИНХРОННАЯ ВЕРСИЯ
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.news import News
from app.schemas.news import NewsCreate, NewsUpdate
from typing import Optional, List


async def create(db: Session, news_in: NewsCreate) -> News:
    """Создание новости"""
    db_news = News(
        title=news_in.title,
        image_url=str(news_in.image_url) if news_in.image_url else None,
        author=news_in.author,
        summary=news_in.summary,
        content=news_in.content,
        tags=news_in.tags or []
    )
    db.add(db_news)
    db.commit()
    db.refresh(db_news)
    return db_news


async def get_all(db: Session) -> List[News]:
    """Получить все новости"""
    return db.query(News).all()


async def get_by_id(db: Session, news_id: int) -> Optional[News]:
    """Получить новость по ID"""
    return db.query(News).filter(News.id == news_id).first()


async def search(db: Session, query: str) -> List[News]:
    """Поиск новостей"""
    search_pattern = f"%{query}%"
    return db.query(News).filter(
        (News.title.ilike(search_pattern)) |
        (News.content.ilike(search_pattern)) |
        (News.summary.ilike(search_pattern))
    ).all()


async def update(db: Session, news_id: int, news_in: NewsUpdate) -> bool:
    """Обновление новости"""
    db_news = db.query(News).filter(News.id == news_id).first()
    if not db_news:
        return False

    update_data = news_in.model_dump(exclude_unset=True)

    # Конвертируем HttpUrl в строку
    if 'image_url' in update_data and update_data['image_url'] is not None:
        update_data['image_url'] = str(update_data['image_url'])

    for field, value in update_data.items():
        setattr(db_news, field, value)

    db.commit()
    db.refresh(db_news)
    return True


async def delete(db: Session, news_id: int) -> bool:
    """Удаление новости"""
    db_news = db.query(News).filter(News.id == news_id).first()
    if not db_news:
        return False

    db.delete(db_news)
    db.commit()
    return True
