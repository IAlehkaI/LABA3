# app/api/routes.py - ОБНОВЛЁННАЯ ВЕРСИЯ

from fastapi import APIRouter, Request, Form, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.schemas.news import NewsCreate, NewsUpdate
from app.services.news_service import news_service
from app.db.session import get_db
from app.core.security import (
    get_current_user_optional,
    require_admin,
    TokenData,
    AnonymousUser
)
from app.utils.s3 import upload_image_to_s3
from typing import Optional, Union
from datetime import datetime
from app.api.auth import router as auth_router
from app.api.news import router as news_router

router = APIRouter()
templates = Jinja2Templates(directory="templates")
router.include_router(auth_router)
router.include_router(news_router, prefix="/api/news", tags=["news"])


# Хелпер для красивой даты в шаблонах
def format_date(dt_obj) -> str:
    """
    Форматирование datetime в красивую строку.
    Поддерживает как строки ISO, так и объекты datetime.
    """
    if isinstance(dt_obj, str):
        dt = datetime.fromisoformat(dt_obj.replace("Z", "+00:00"))
    else:
        dt = dt_obj

    months = ["", "января", "февраля", "марта", "апреля", "мая", "июня",
              "июля", "августа", "сентября", "октября", "ноября", "декабря"]
    return f"{dt.day} {months[dt.month]} {dt.year} г."


templates.env.globals["format_date"] = format_date


# === ВЕБ-ЧАСТЬ (ДОСТУПНА АНОНИМАМ) ===

@router.get("/", response_class=HTMLResponse)
async def home(
        request: Request,
        q: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: Union[TokenData, AnonymousUser] = Depends(get_current_user_optional),
):
    """Главная страница - доступна всем, включая анонимов"""
    search_query = (q or "").strip()
    news_list = await news_service.search(db, search_query) if search_query else await news_service.get_all(db)

    top_news = news_list[:3] if not search_query else []
    news_list = news_list[3:] if not search_query else news_list

    return templates.TemplateResponse("index.html", {
        "request": request,
        "top_news": top_news,
        "news_list": news_list,
        "search_query": search_query,
        "current_user": current_user,  # ← ВАЖНО: передаём пользователя
    })


@router.get("/news/{news_id}", response_class=HTMLResponse)
async def news_detail(
        request: Request,
        news_id: int,
        db: Session = Depends(get_db),
        current_user: Union[TokenData, AnonymousUser] = Depends(get_current_user_optional)
):
    """Детали новости - доступны всем"""
    news = await news_service.get_by_id(db, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    return templates.TemplateResponse("news_detail.html", {
        "request": request,
        "news": news,
        "current_user": current_user,  # ← ВАЖНО: передаём пользователя
    })


# === ТОЛЬКО ДЛЯ АДМИНИСТРАТОРОВ ===

@router.get("/create", response_class=HTMLResponse)
async def create_form(
        request: Request,
        current_user: TokenData = Depends(require_admin)
):
    """Форма создания новости - только для админов"""
    return templates.TemplateResponse("create.html", {
        "request": request,
        "current_user": current_user  # ← ВАЖНО: передаём пользователя
    })


@router.post("/create")
async def create_news(
        request: Request,
        title: str = Form(...),
        author: str = Form(...),
        summary: str = Form(...),
        content: str = Form(...),
        image_url: Optional[str] = Form(""),
        image_file: Optional[UploadFile] = File(None),
        tags: Optional[str] = Form(""),
        db: Session = Depends(get_db),
        current_user: TokenData = Depends(require_admin),
):
    """Создание новости - только для админов"""
    final_image_url = image_url
    if image_file and image_file.filename:
        contents = await image_file.read()
        final_image_url = await upload_image_to_s3(contents, image_file.filename)

    news_in = NewsCreate(
        title=title,
        author=author,
        summary=summary,
        content=content,
        image_url=final_image_url or None,
        tags=[t.strip() for t in tags.split(",") if t.strip()] if tags else [],
    )

    await news_service.create(db, news_in)
    return RedirectResponse(url="/", status_code=303)


@router.get("/edit/{news_id}", response_class=HTMLResponse)
async def edit_form(
        request: Request,
        news_id: int,
        db: Session = Depends(get_db),
        current_user: TokenData = Depends(require_admin),
):
    """Форма редактирования - только для админов"""
    news = await news_service.get_by_id(db, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    tags_str = ", ".join(news.tags) if news.tags else ""

    return templates.TemplateResponse("edit.html", {
        "request": request,
        "news": news,
        "tags_str": tags_str,
        "current_user": current_user,  # ← ВАЖНО: передаём пользователя
    })


@router.post("/edit/{news_id}")
async def update_news(
        news_id: int,
        title: str = Form(...),
        author: str = Form(...),
        summary: str = Form(...),
        content: str = Form(...),
        image_url: Optional[str] = Form(""),
        image_file: Optional[UploadFile] = File(None),
        tags: Optional[str] = Form(""),
        db: Session = Depends(get_db),
        current_user: TokenData = Depends(require_admin),
):
    """Обновление новости - только для админов"""
    final_image_url = image_url
    if image_file and image_file.filename:
        contents = await image_file.read()
        final_image_url = await upload_image_to_s3(contents, image_file.filename)

    news_update = NewsUpdate(
        title=title,
        author=author,
        summary=summary,
        content=content,
        image_url=final_image_url or None,
        tags=[t.strip() for t in tags.split(",") if t.strip()] if tags else [],
    )

    success = await news_service.update(db, news_id, news_update)
    if not success:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    return RedirectResponse(url=f"/news/{news_id}", status_code=303)


@router.post("/delete/{news_id}")
async def delete_news(
        news_id: int,
        db: Session = Depends(get_db),
        current_user: TokenData = Depends(require_admin),
):
    """Удаление новости - только для админов"""
    success = await news_service.delete(db, news_id)
    if not success:
        raise HTTPException(status_code=404, detail="Новость не найдена")
    return RedirectResponse(url="/", status_code=303)


# === СТРАНИЦА ЛОГИНА ===
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница авторизации"""
    return templates.TemplateResponse("login.html", {"request": request})


# === ВЫХОД ИЗ СИСТЕМЫ ===
@router.get("/logout", response_class=HTMLResponse)
async def logout_page(request: Request):
    """Страница выхода из системы"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Выход</title>
        <script>
            localStorage.removeItem('token');
            localStorage.removeItem('username');
            alert('✅ Вы вышли из системы');
            window.location.href = '/';
        </script>
    </head>
    <body>
        <p style="text-align: center; padding: 50px; font-family: Arial;">
            Выход из системы...
        </p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
