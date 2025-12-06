# app/core/security.py — ПОЛНАЯ СИСТЕМА РОЛЕЙ
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# === НАСТРОЙКИ ===
SECRET_KEY = "super-secret-jwt-key-change-in-prod-2025"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 часа

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


# === ПАРОЛИ ===
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    return pwd_context.hash(password)


# === JWT ===
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Декодирует токен без выбрасывания ошибки"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# === МОДЕЛИ ПОЛЬЗОВАТЕЛЕЙ ===
class AnonymousUser(BaseModel):
    """Анонимный пользователь (без авторизации)"""
    username: str = "anonymous"
    role: str = "anonymous"
    is_authenticated: bool = False


class AuthenticatedUser(BaseModel):
    """Авторизованный пользователь (reader, author, admin)"""
    username: str
    role: str  # reader, author, admin
    is_authenticated: bool = True
    user_id: int = None


# === ПОЛУЧЕНИЕ ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ ===

async def get_current_user_optional(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[AuthenticatedUser | AnonymousUser]:
    """
    Возвращает пользователя из токена или AnonymousUser.
    РАЗРЕШАЕТ АНОНИМНЫЙ ДОСТУП - не выбрасывает ошибку 401
    """
    if not credentials:
        return AnonymousUser()

    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        return AnonymousUser()

    username = payload.get("sub")
    role = payload.get("role", "reader")
    user_id = payload.get("user_id")

    if not username:
        return AnonymousUser()

    return AuthenticatedUser(
        username=username,
        role=role,
        user_id=user_id
    )


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security)
) -> AuthenticatedUser:
    """
    ТРЕБУЕТ авторизации. Выбрасывает 401 если токена нет.
    Используйте для защищённых эндпоинтов.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("sub")
    role = payload.get("role", "reader")
    user_id = payload.get("user_id")

    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthenticatedUser(
        username=username,
        role=role,
        user_id=user_id
    )


# === ПРОВЕРКА РОЛЕЙ ===

def require_reader(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    """Требует минимум роль reader (reader, author, admin)"""
    if user.role not in ["reader", "author", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется авторизация"
        )
    return user


def require_author(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    """Требует минимум роль author (author, admin)"""
    if user.role not in ["author", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль автора или администратора"
        )
    return user


def require_admin(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    """Требует роль admin"""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль администратора"
        )
    return user
