# app/main.py — с middleware для авторизации из cookies/headers
import threading
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.init_data import load_initial_data
from app.api.routes import router as web_router
from app.grpc.server import serve_grpc
from app.db.session import engine
from app.db.base import Base
from app.core.config import settings
from app.utils.s3 import s3_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Новостник 2025",
    description="Полноценный новостной сервис с REST + gRPC + S3 + Redis + ролями",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === MIDDLEWARE ДЛЯ АВТОРИЗАЦИИ ИЗ COOKIES ===
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """
    Автоматически добавляет токен из cookies в заголовок Authorization
    """
    token = request.cookies.get("access_token")
    if token and not request.headers.get("Authorization"):
        # Создаём новый scope с добавленным заголовком
        headers = dict(request.headers)
        headers["authorization"] = f"Bearer {token}"
        request._headers = headers

    response = await call_next(request)
    return response


app.include_router(web_router)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def run_grpc_server():
    try:
        serve_grpc()
    except Exception as e:
        logger.error(f"gRPC сервер упал: {e}")


@app.on_event("startup")
async def on_startup():
    logger.info("Запуск приложения...")
    Base.metadata.create_all(bind=engine)
    logger.info("Таблицы БД созданы/обновлены")

    try:
        s3_client.create_bucket(Bucket=settings.S3_BUCKET)
        logger.info(f"Бакет {settings.S3_BUCKET} создан")
    except s3_client.exceptions.BucketAlreadyOwnedByYou:
        logger.info(f"Бакет {settings.S3_BUCKET} уже существует")
    except Exception as e:
        logger.warning(f"Не удалось создать бакет: {e}")

    grpc_thread = threading.Thread(target=run_grpc_server, daemon=True)
    grpc_thread.start()
    logger.info("gRPC-сервер запущен на порту 50051")

    load_initial_data()
    logger.info("Приложение полностью готово!")


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Остановка приложения...")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

from app.core.security import create_access_token


@app.get("/get-token")
async def get_token():
    token = create_access_token({"sub": "admin", "is_admin": True})
    return {"access_token": token, "token_type": "bearer"}
