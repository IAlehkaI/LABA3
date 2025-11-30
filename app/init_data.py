# app/init_data.py
import os
import json
from datetime import datetime

from app.db.session import SessionLocal
from app.models.news import News
from app.models.user import User
from app.core.security import get_password_hash

def load_initial_data():
    db = SessionLocal()

    # === Создаём админа, если его ещё нет ===
    if not db.query(User).filter(User.username == "admin").first():
        admin = User(
            username="admin",
            email="admin@news.ru",
            hashed_password=get_password_hash("admin123"),
            is_admin=True
        )
        db.add(admin)
        db.commit()
        print("Создан админ: admin / admin123")

    # === Загружаем новости, если их нет ===
    if db.query(News).count() == 0:
        file_path = os.path.join(os.path.dirname(__file__), "..", "data", "initial_news.json")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                news = News(**item)
                db.add(news)
            db.commit()
            print(f"Загружено {len(data)} начальных новостей")
        else:
            print("initial_news.json не найден — новости не загружены")

    db.close()