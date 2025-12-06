# app/api/routes.py — ПОЛНАЯ ВЕРСИЯ С 4 РОЛЯМИ

from fastapi import APIRouter, Request, Form, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.schemas.news import NewsCreate, NewsUpdate
from app.services.news_service import news_service
from app.db.session import get_db
from app.core.security import (
    get_current_user_optional,
    get_current_user,
    require_author,
    require_admin,
    AuthenticatedUser,
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
    if isinstance(dt_obj, str):
        dt = datetime.fromisoformat(dt_obj.replace("Z", "+00:00"))
    else:
        dt = dt_obj

    months = ["", "января", "февраля", "марта", "апреля", "мая", "июня",
              "июля", "августа", "сентября", "октября", "ноября", "декабря"]
    return f"{dt.day} {months[dt.month]} {dt.year} г."


templates.env.globals["format_date"] = format_date


# === ПУБЛИЧНЫЕ ЭНДПОИНТЫ (ДОСТУПНЫ АНОНИМАМ) ===

@router.get("/", response_class=HTMLResponse)
async def home(
        request: Request,
        q: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: Union[AuthenticatedUser, AnonymousUser] = Depends(get_current_user_optional),
):
    """Главная страница - доступна всем"""
    search_query = (q or "").strip()
    news_list = await news_service.search(db, search_query) if search_query else await news_service.get_all(db)

    top_news = news_list[:3] if not search_query else []
    news_list = news_list[3:] if not search_query else news_list

    return templates.TemplateResponse("index.html", {
        "request": request,
        "top_news": top_news,
        "news_list": news_list,
        "search_query": search_query,
        "current_user": current_user,
    })


@router.get("/news/{news_id}", response_class=HTMLResponse)
async def news_detail(
    request: Request,
    news_id: int,
    db: Session = Depends(get_db),
    current_user: Union[AuthenticatedUser, AnonymousUser] = Depends(get_current_user_optional)
):
    """Детали новости - доступны всем"""
    news = await news_service.get_by_id(db, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    # Отслеживаем прочтение для авторизованных пользователей
    if current_user.is_authenticated:
        from app.models.user import User
        user = db.query(User).filter(User.id == current_user.user_id).first()
        if user:
            if not user.read_history:
                user.read_history = []
            if news_id not in user.read_history:
                user.read_history.append(news_id)
                if len(user.read_history) > 100:
                    user.read_history = user.read_history[-100:]
                db.commit()

    return templates.TemplateResponse("news_detail.html", {
        "request": request,
        "news": news,
        "current_user": current_user,
    })

# === СТРАНИЦЫ АВТОРИЗАЦИИ ===

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница авторизации"""
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/logout", response_class=HTMLResponse)
async def logout_page(request: Request):
    """Выход из системы"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Выход</title>
        <script>
            localStorage.removeItem('token');
            localStorage.removeItem('username');
            localStorage.removeItem('role');
            alert('✅ Вы вышли из системы');
            window.location.href = '/';
        </script>
    </head>
    <body style="text-align: center; padding: 50px; font-family: Arial;">
        <p>Выход из системы...</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# === ТОЛЬКО ДЛЯ АВТОРОВ И АДМИНОВ ===

@router.get("/create", response_class=HTMLResponse)
async def create_form(
        request: Request,
        current_user: AuthenticatedUser = Depends(require_author)
):
    """Форма создания новости - только для авторов и админов"""
    return templates.TemplateResponse("create.html", {
        "request": request,
        "current_user": current_user
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
        current_user: AuthenticatedUser = Depends(require_author),
):
    """Создание новости - только для авторов и админов"""
    # Для авторов - автоматически используется их имя
    final_author = author if current_user.role == "admin" else current_user.username

    final_image_url = image_url
    if image_file and image_file.filename:
        contents = await image_file.read()
        final_image_url = await upload_image_to_s3(contents, image_file.filename)

    news_in = NewsCreate(
        title=title,
        author=final_author,
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
        current_user: AuthenticatedUser = Depends(require_author),
):
    """Форма редактирования - авторы могут редактировать только свои новости"""
    news = await news_service.get_by_id(db, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    # Проверяем права доступа
    if current_user.role == "author" and news.author != current_user.username:
        raise HTTPException(status_code=403, detail="Вы можете редактировать только свои новости")

    tags_str = ", ".join(news.tags) if news.tags else ""

    return templates.TemplateResponse("edit.html", {
        "request": request,
        "news": news,
        "tags_str": tags_str,
        "current_user": current_user,
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
        current_user: AuthenticatedUser = Depends(require_author),
):
    """Обновление новости"""
    news = await news_service.get_by_id(db, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    # Проверяем права доступа
    if current_user.role == "author" and news.author != current_user.username:
        raise HTTPException(status_code=403, detail="Вы можете редактировать только свои новости")

    # Для авторов - используется их имя
    final_author = author if current_user.role == "admin" else current_user.username

    final_image_url = image_url
    if image_file and image_file.filename:
        contents = await image_file.read()
        final_image_url = await upload_image_to_s3(contents, image_file.filename)

    news_update = NewsUpdate(
        title=title,
        author=final_author,
        summary=summary,
        content=content,
        image_url=final_image_url or None,
        tags=[t.strip() for t in tags.split(",") if t.strip()] if tags else [],
    )

    success = await news_service.update(db, news_id, news_update)
    if not success:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    return RedirectResponse(url=f"/news/{news_id}", status_code=303)


# === ТОЛЬКО ДЛЯ АДМИНИСТРАТОРОВ ===
@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Страница регистрации"""
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/delete/{news_id}")
async def delete_news(
        news_id: int,
        db: Session = Depends(get_db),
        current_user: AuthenticatedUser = Depends(require_admin),
):
    """Удаление новости - только для админов"""
    success = await news_service.delete(db, news_id)
    if not success:
        raise HTTPException(status_code=404, detail="Новость не найдена")
    return RedirectResponse(url="/", status_code=303)


# === ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ ===

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
        request: Request,
        db: Session = Depends(get_db),
        current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Страница профиля пользователя"""
    from app.models.user import User

    # Получаем полные данные пользователя из БД
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Получаем историю прочитанных новостей
    read_news = []
    if user.read_history and len(user.read_history) > 0:
        news_ids = user.read_history[-20:]  # Последние 20
        from app.models.news import News
        read_news = db.query(News).filter(News.id.in_(news_ids)).all()
        read_news.reverse()  # От новых к старым

    # Для авторов - получаем их статьи
    author_articles = []
    if user.role in ["author", "admin"]:
        from app.models.news import News
        if user.role == "author":
            author_articles = db.query(News).filter(News.author == user.username).order_by(News.created_at.desc()).all()
        else:
            author_articles = db.query(News).order_by(News.created_at.desc()).limit(10).all()

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "current_user": current_user,
        "user": user,
        "read_news": read_news,
        "author_articles": author_articles
    })


@router.post("/track-read/{news_id}")
async def track_read(
        news_id: int,
        db: Session = Depends(get_db),
        current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Отслеживание прочитанной новости"""
    from app.models.user import User

    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        return {"status": "error"}

    # Добавляем в историю, если ещё не добавлено
    if not user.read_history:
        user.read_history = []

    if news_id not in user.read_history:
        user.read_history.append(news_id)
        # Ограничиваем историю 100 последними новостями
        if len(user.read_history) > 100:
            user.read_history = user.read_history[-100:]

        db.commit()

    return {"status": "ok"}
