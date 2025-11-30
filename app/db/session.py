# app/db/session.py
# Управление подключением к базе и сессиями

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from app.core.config import settings

# Создаём движок — один на всё приложение
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,                 # поставь True, если хочешь видеть SQL-запросы в логах
    pool_pre_ping=True,              # защита от отвалившихся соединений
    pool_recycle=3600,               # перезапускаем соединения раз в час
)

# Фабрика сессий
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Потокобезопасная обёртка — удобно для async/многопоточности
SessionLocal = scoped_session(SessionLocal)


def get_db():
    """
    Зависимость для FastAPI.
    Используется так: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()