# app/api/routes.py

from fastapi import APIRouter, Request, Form, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.schemas.news import NewsCreate, NewsUpdate
from app.services.news_service import news_service
from app.core.security import get_current_user, require_role
from app.core.roles import Role
from app.utils.s3 import upload_image_to_s3  # если используешь загрузку файлов
from typing import Optional
from app.api.auth import router as auth_router
from app.api.news import router as news_router
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")
router = APIRouter()

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница авторизации"""
    return templates.TemplateResponse("login.html", {"request": request})

router = APIRouter()
templates = Jinja2Templates(directory="templates")
router.include_router(auth_router)      # ← авторизация
router.include_router(news_router, prefix="/news", tags=["news"])  # ← новости
# Хелпер для красивой даты в шаблонах
def format_date(iso_string: str) -> str:
    from datetime import datetime
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    months = ["", "января", "февраля", "марта", "апреля", "мая", "июня",
              "июля", "августа", "сентября", "октября", "ноября", "декабря"]
    return f"{dt.day} {months[dt.month]} {dt.year} г."

templates.env.globals["format_date"] = format_date


# === ВЕБ-ЧАСТЬ (HTML + Tailwind) ===

@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    q: Optional[str] = None,
    current_user: dict = Depends(get_current_user),  # может быть None — аноним
):
    search_query = (q or "").strip()
    news_list = await news_service.search(search_query) if search_query else await news_service.get_all()

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
async def news_detail(request: Request, news_id: int, current_user: dict = Depends(get_current_user)):
    news = await news_service.get_by_id(news_id)
    if not news:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    return templates.TemplateResponse("news_detail.html", {
        "request": request,
        "news": news,
        "current_user": current_user,
    })


@router.get("/create", response_class=HTMLResponse)
async def create_form(request: Request, current_user: dict = Depends(require_role(Role.ADMIN))):
    return templates.TemplateResponse("create.html", {"request": request, "current_user": current_user})


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
    current_user: dict = Depends(require_role(Role.ADMIN)),
):
    # Если загрузили файл — заливаем в S3, иначе берём URL
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

    await news_service.create(news_in)
    return RedirectResponse(url="/", status_code=303)


@router.get("/edit/{news_id}", response_class=HTMLResponse)
async def edit_form(
    request: Request,
    news_id: int,
    current_user: dict = Depends(require_role(Role.ADMIN)),
):
    news = await news_service.get_by_id(news_id)
    if not news:
        raise HTTPException(status_code=404, detail="Новость не найдена")

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
    current_user: dict = Depends(require_role(Role.ADMIN)),
):
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

    success = await news_service.update(news_id, news_update)
    if not success:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    return RedirectResponse(url=f"/news/{news_id}", status_code=303)


@router.post("/delete/{news_id}")
async def delete_news(
    news_id: int,
    current_user: dict = Depends(require_role(Role.ADMIN)),
):
    success = await news_service.delete(news_id)
    if not success:
        raise HTTPException(status_code=404, detail="Новость не найдена")
    return RedirectResponse(url="/", status_code=303)

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница авторизации"""
    return templates.TemplateResponse("login.html", {"request": request})
