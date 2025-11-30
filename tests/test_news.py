# tests/test_news.py
import pytest
from httpx import AsyncClient
from app.main import app
from app.core.security import create_access_token
from app.core.roles import Role

# Фикстура клиента
@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# Токен админа
def admin_token():
    return create_access_token({"sub": "admin", "role": Role.ADMIN})


# Токен обычного пользователя (не админа)
def user_token():
    return create_access_token({"sub": "user", "role": Role.USER})


@pytest.mark.asyncio
async def test_create_news_as_admin(client: AsyncClient):
    headers = {"Authorization": f"Bearer {admin_token()}"}

    form_data = {
        "title": "Тестовая новость",
        "author": "Тестер",
        "summary": "Краткое описание для теста",
        "content": "Полный текст новости для тестового прогона",
        "tags": "тест, pytest"
    }

    response = await client.post("/create", data=form_data, headers=headers)
    assert response.status_code == 303  # редирект после создания
    assert response.headers["location"] == "/"


@pytest.mark.asyncio
async def test_create_news_unauthorized(client: AsyncClient):
    # Без токена
    response = await client.get("/create")
    assert response.status_code == 401

    # С токеном обычного пользователя
    headers = {"Authorization": f"Bearer {user_token()}"}
    response = await client.get("/create", headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_edit_news_as_admin(client: AsyncClient):
    headers = {"Authorization": f"Bearer {admin_token()}"}

    # Сначала создаём новость
    await client.post("/create", data={
        "title": "Для редактирования",
        "author": "Админ",
        "summary": "Старая версия",
        "content": "Старый контент",
    }, headers=headers)

    # Получаем последнюю новость (предполагаем, что она первая)
    resp = await client.get("/")
    news_id = resp.text.split('/news/')[1].split('"')[0]

    # Редактируем
    response = await client.post(f"/edit/{news_id}", data={
        "title": "Обновлённая новость!",
        "author": "Админ 2",
        "summary": "Новое краткое",
        "content": "Новый полный текст",
        "tags": "обновлено, тест"
    }, headers=headers, follow_redirects=True)

    assert response.status_code == 200
    assert "Обновлённая новость!" in response.text


@pytest.mark.async740
async def test_delete_news_as_admin(client: AsyncClient):
    headers = {"Authorization": f"Bearer {admin_token()}"}

    # Создаём
    await client.post("/create", data={
        "title": "Удаляем эту",
        "author": "Админ",
        "summary": "Скоро исчезнет",
        "content": "Пока-пока"
    }, headers=headers)

    resp = await client.get("/")
    news_id = resp.text.split('/news/')[1].split('"')[0]

    response = await client.post(f"/delete/{news_id}", headers=headers, follow_redirects=True)
    assert response.status_code == 200
    assert "Удаляем эту" not in response.text  # её больше нет


@pytest.mark.asyncio
async def test_search(client: AsyncClient):
    headers = {"Authorization": f"Bearer {admin_token()}"}

    await client.post("/create", data={
        "title": "Уникальная новость про Python",
        "author": "Pythonista",
        "summary": "Тут про змею",
        "content": "Python — лучший язык!"
    }, headers=headers)

    response = await client.get("/?q=Python")
    assert response.status_code == 200
    assert "Уникальная новость про Python" in response.text
    assert "Главные новости" not in response.text  # карусель скрывается при поиске


@pytest.mark.asyncio
async def test_home_page_anonymous(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    assert "Новостник" in response.text
    assert "Добавить новость" not in response.text  # кнопка + только для админа


@pytest.mark.asyncio
async def test_upload_image_via_file(client: AsyncClient):
    headers = {"Authorization": f"Bearer {admin_token()}"}

    # Создаём простую картинку в памяти
    from io import BytesIO
    from PIL import Image

    img_io = BytesIO()
    img = Image.new("RGB", (100, 100), color="red")
    img.save(img_io, format="JPEG")
    img_io.seek(0)

    files = {"image_file": ("test.jpg", img_io, "image/jpeg")}
    data = {
        "title": "С картинкой",
        "author": "Фотограф",
        "summary": "Тест загрузки",
        "content": "Есть изображение"
    }

    response = await client.post("/create", data=data, files=files, headers=headers)
    assert response.status_code == 303

    # Проверяем, что картинка отображается
    resp = await client.get("/")
    assert "test.jpg" in resp.text or "http://localhost:9000" in resp.text