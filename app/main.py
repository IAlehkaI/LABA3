# app/main.py — ФИНАЛЬНЫЙ РАБОЧИЙ ВАРИАНТ (30 ноября 2025)
import threading
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.init_data import load_initial_data
from app.api.routes import router as web_router
from app.grpc.server import serve_grpc  # ← gRPC сервер
from app.db.session import engine
from app.db.base import Base
from app.core.config import settings
from app.utils.s3 import s3_client
from app.api import routes

app.include_router(routes.router)

# Логи
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI приложение
app = FastAPI(
    title="Новостник 2025",
    description="Полноценный новостной сервис с REST + gRPC + S3 + Redis + ролями",
    version="3.0.0",
)

# CORS (на всякий случай)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роуты и статику
app.include_router(web_router)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Глобальная переменная для текущего пользователя (для шаблонов)
@app.middleware("http")
async def add_current_user(request: Request, call_next):
    user = None
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        from app.core.security import decode_access_token
        token = auth.split(" ")[1]
        payload = decode_access_token(token)
        if payload:
            user = type("obj", (object,), payload)  # имитируем объект пользователя
    request.state.user = user
    response = await call_next(request)
    return response

# === Запуск gRPC в отдельном потоке (чтобы не блокировать asyncio) ===
def run_grpc_server():
    try:
        serve_grpc()  # из app/grpc/server.py
    except Exception as e:
        logger.error(f"gRPC сервер упал: {e}")

@app.on_event("startup")
async def on_startup():
    logger.info("Запуск приложения...")

    # 1. Создаём таблицы
    Base.metadata.create_all(bind=engine)
    logger.info("Таблицы БД созданы/обновлены")

    # 2. Создаём бакет в MinIO
    try:
        s3_client.create_bucket(Bucket=settings.S3_BUCKET)
        logger.info(f"Бакет {settings.S3_BUCKET} создан")
    except s3_client.exceptions.BucketAlreadyOwnedByYou:
        logger.info(f"Бакет {settings.S3_BUCKET} уже существует")
    except Exception as e:
        logger.warning(f"Не удалось создать бакет: {e}")

    # 3. Запускаем gRPC в отдельном потоке
    grpc_thread = threading.Thread(target=run_grpc_server, daemon=True)
    grpc_thread.start()
    logger.info("gRPC-сервер запущен на порту 50051")

    from app.init_data import load_initial_data
    load_initial_data()

    logger.info("Приложение полностью готово!")

# Для локального запуска через uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

# ВРЕМЕННЫЙ ЭНДПОИНТ — ТОЛЬКО ДЛЯ ТЕСТА И СДАЧИ!
from app.core.security import create_access_token

@app.get("/get-token")
async def get_token():
    token = create_access_token({"sub": "admin", "is_admin": True})
    return {"access_token": token, "token_type": "bearer"}