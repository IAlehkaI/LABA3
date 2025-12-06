# app/api/news.py — РАБОЧИЙ РОУТЕР НОВОСТЕЙ (2025)
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.news import News
from app.core.security import get_current_user, require_role
from app.utils.s3 import upload_image_to_s3
import logging
from typing import Optional

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)

# Главная страница
@router.get("/", response_class=HTMLResponse)
async def home(request: dict, db: Session = Depends(get_db), user: Optional[dict] = Depends(get_current_user, use_cache=False) or None):
    news_list = db.query(News).order_by(News.created_at.desc()).all()
    top_news = news_list[:3] if len(news_list) >= 3 else []
    other_news = news_list[3:] if len(news_list) >= 3 else news_list
    return templates.TemplateResponse("index.html", {
        "request": request,
        "top_news": top_news,
        "news_list": other_news,
        "current_user": user,
    })

# Детали новости
@router.get("/news/{news_id}", response_class=HTMLResponse)
async def news_detail(request: dict, news_id: int, db: Session = Depends(get_db)):
    news = db.query(News).filter(News.id == news_id).first()
    if not news:
        raise HTTPException(404, "Новость не найдена")
    return templates.TemplateResponse("news_detail.html", {"request": request, "news": news})

# Форма создания
@router.get("/create", response_class=HTMLResponse)
async def create_form(request: dict, user=Depends(require_role("admin"))):
    return templates.TemplateResponse("create.html", {"request": request})

# Создание новости
@router.post("/create")
async def create_news(
    title: str = Form(...),
    author: str = Form(...),
    summary: str = Form(...),
    content: str = Form(...),
    image_file: UploadFile = File(None),
    tags: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin"))
):
    image_url = None
    if image_file and image_file.filename:
        contents = await image_file.read()
        image_url = await upload_image_to_s3(contents, image_file.filename)

    news = News(
        title=title,
        author=author,
        summary=summary,
        content=content,
        image_url=image_url,
        tags=[t.strip() for t in tags.split(",") if t.strip()]
    )
    db.add(news)
    db.commit()
    return RedirectResponse("/", status_code=303)

# Удаление
@router.post("/delete/{news_id}")
async def delete(news_id: int, db: Session = Depends(get_db), user=Depends(require_role("admin"))):
    news = db.query(News).filter(News.id == news_id).first()
    if not news:
        raise HTTPException(404)
    db.delete(news)
    db.commit()
    return RedirectResponse("/", status_code=303)