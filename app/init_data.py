# app/init_data.py — С АВТОМАТИЧЕСКИМ СБРОСОМ SEQUENCE
from sqlalchemy import text
from app.db.session import SessionLocal
from app.models.user import User
from app.models.news import News
from app.core.security import get_password_hash


def load_initial_data():
    db = SessionLocal()
    try:
        # === ПОЛЬЗОВАТЕЛИ ===
        if not db.query(User).filter(User.username == "admin").first():
            users = [
                User(
                    username="admin",
                    email="admin@news.ru",
                    hashed_password=get_password_hash("admin"),
                    role="admin",
                    read_history=[]
                ),
                User(
                    username="author",
                    email="author@news.ru",
                    hashed_password=get_password_hash("author123"),
                    role="author",
                    read_history=[]
                ),
                User(
                    username="reader",
                    email="reader@news.ru",
                    hashed_password=get_password_hash("reader123"),
                    role="reader",
                    read_history=[]
                ),
            ]
            for user in users:
                db.add(user)
                db.commit()
                db.refresh(user)
                print(
                    f"✅ Создан {user.role}: {user.username} / {'admin' if user.role == 'admin' else user.username + '123'} (role={user.role})")

        # === НОВОСТИ ===
        if db.query(News).count() == 0:
            news_list = [
                News(
                    title="Новая эра искусственного интеллекта",
                    author="AI Research Team",
                    content="Революционные достижения в области машинного обучения открывают новые горизонты для человечества. Нейросети теперь способны не только анализировать данные, но и создавать оригинальный контент.",
                    summary="Прорыв в области ИИ меняет мир технологий",
                    image_url="https://images.unsplash.com/photo-1677442136019-21780ecad995?w=1200&h=800&fit=crop",
                    tags=["технологии", "ИИ", "наука"]
                ),
                News(
                    title="Зелёная энергетика набирает обороты",
                    author="EcoNews",
                    content="Возобновляемые источники энергии становятся основным трендом в мировой энергетике. Солнечные панели и ветрогенераторы теперь доступнее, чем когда-либо.",
                    summary="Переход на зелёную энергию ускоряется",
                    image_url="https://images.unsplash.com/photo-1473341304170-971dccb5ac1e?w=1200&h=800&fit=crop",
                    tags=["экология", "энергетика", "будущее"]
                ),
                News(
                    title="Космический туризм становится реальностью",
                    author="Space Today",
                    content="Частные космические компании предлагают первые коммерческие полёты на околоземную орбиту. Цены снижаются, а желающих становится всё больше.",
                    summary="Полёты в космос теперь доступны туристам",
                    image_url="https://images.unsplash.com/photo-1516849841032-87cbac4d88f7?w=1200&h=800&fit=crop",
                    tags=["космос", "туризм", "технологии"]
                ),
            ]

            for news_item in news_list:
                db.add(news_item)

            db.commit()
            print(f"✅ Загружено {len(news_list)} начальных новостей")

            # === КРИТИЧНО: СБРОС SEQUENCE ПОСЛЕ ЗАГРУЗКИ ===
            db.execute(text("SELECT setval('news_id_seq', (SELECT MAX(id) FROM news))"))
            db.execute(text("SELECT setval('users_id_seq', (SELECT MAX(id) FROM users))"))
            db.commit()
            print("✅ Sequences синхронизированы")

    except Exception as e:
        print(f"❌ Ошибка загрузки начальных данных: {e}")
        db.rollback()
    finally:
        db.close()
