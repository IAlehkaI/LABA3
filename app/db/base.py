# app/db/base.py
# Здесь только базовый класс для всех моделей

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """
    Базовый класс для всех SQLAlchemy-моделей.
    Ничего лишнего — просто наследуемся от него в models/news.py
    """
    pass