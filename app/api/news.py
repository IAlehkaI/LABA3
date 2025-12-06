# app/api/news.py — ОБНОВЛЁННАЯ ВЕРСИЯ С НОВЫМИ ИМПОРТАМИ
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Union
from app.schemas.news import NewsResponse, NewsCreate, NewsUpdate
from app.services.news_service import news_service
from app.db.session import get_db
from app.core.security import (
    get_current_user_optional,
    require_admin,
    AuthenticatedUser,  # ← ИЗМЕНЕНО с TokenData
    AnonymousUser
)

router = APIRouter()


# === ПУБЛИЧНЫЕ ЭНДПОИНТЫ (ЧТЕНИЕ) - ДОСТУПНЫ АНОНИМАМ ===

@router.get("/", response_model=List[NewsResponse])
async def get_all_news(
        db: Session = Depends(get_db),
        current_user: Union[AuthenticatedUser, AnonymousUser] = Depends(get_current_user_optional)
):
    """
    Получить все новости.
    Доступно: анонимам, пользователям, админам
    """
    return await news_service.get_all(db)


@router.get("/search", response_model=List[NewsResponse])
async def search_news(
        q: str,
        db: Session = Depends(get_db),
        current_user: Union[AuthenticatedUser, AnonymousUser] = Depends(get_current_user_optional)
):
    """
    Поиск новостей по запросу.
    Доступно: анонимам, пользователям, админам
    """
    return await news_service.search(db, q)


@router.get("/{news_id}", response_model=NewsResponse)
async def get_news_by_id(
        news_id: int,
        db: Session = Depends(get_db),
        current_user: Union[AuthenticatedUser, AnonymousUser] = Depends(get_current_user_optional)
):
    """
    Получить новость по ID.
    Доступно: анонимам, пользователям, админам
    """
    news = await news_service.get_by_id(db, news_id)
    if not news:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Новость не найдена"
        )
    return news


# === ЗАЩИЩЁННЫЕ ЭНДПОИНТЫ - ТОЛЬКО ДЛЯ АДМИНИСТРАТОРОВ ===

@router.post("/", response_model=NewsResponse, status_code=status.HTTP_201_CREATED)
async def create_news(
        news_in: NewsCreate,
        db: Session = Depends(get_db),
        current_user: AuthenticatedUser = Depends(require_admin)
):
    """
    Создать новую новость.
    Доступно: только админам
    """
    return await news_service.create(db, news_in)


@router.put("/{news_id}", response_model=NewsResponse)
async def update_news(
        news_id: int,
        news_update: NewsUpdate,
        db: Session = Depends(get_db),
        current_user: AuthenticatedUser = Depends(require_admin)
):
    """
    Обновить существующую новость.
    Доступно: только админам
    """
    success = await news_service.update(db, news_id, news_update)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Новость не найдена"
        )

    updated_news = await news_service.get_by_id(db, news_id)
    return updated_news


@router.delete("/{news_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_news(
        news_id: int,
        db: Session = Depends(get_db),
        current_user: AuthenticatedUser = Depends(require_admin)
):
    """
    Удалить новость.
    Доступно: только админам
    """
    success = await news_service.delete(db, news_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Новость не найдена"
        )
    return None


@router.get("/by-tag/{tag}", response_model=List[NewsResponse])
async def get_news_by_tag(
        tag: str,
        db: Session = Depends(get_db),
        current_user: Union[AuthenticatedUser, AnonymousUser] = Depends(get_current_user_optional)
):
    """
    Получить новости по тегу.
    Доступно: анонимам, пользователям, админам
    """
    all_news = await news_service.get_all(db)
    filtered = [news for news in all_news if tag in (news.tags or [])]
    return filtered
