# app/models/news.py
# SQLAlchemy-модель новости

from sqlalchemy import Column, Integer, String, Text, DateTime, ARRAY
from sqlalchemy.sql import func
from app.db.base import Base
from typing import List


class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(200), nullable=False, index=True)
    author = Column(String(100), nullable=False)

    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)

    image_url = Column(Text, nullable=True)  # Может быть None — тогда без картинки

    # Теги как массив строк в PostgreSQL
    tags = Column(ARRAY(String), nullable=True, default=list)

    # Автоматически ставится при создании
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    def __repr__(self) -> str:
        return f"<News {self.id}: {self.title[:50]}...>"

    # Удобно для отладки и логов
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "content": self.content,
            "summary": self.summary,
            "image_url": self.image_url,
            "tags": self.tags or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }