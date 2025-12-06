# app/core/security.py — ПОЛНАЯ ВЕРСИЯ С ПОДДЕРЖКОЙ COOKIES
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

SECRET_KEY = "super-secret-jwt-key-change-in-prod-2025"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


class AnonymousUser(BaseModel):
    username: str = "anonymous"
    role: str = "anonymous"
    is_authenticated: bool = False


class AuthenticatedUser(BaseModel):
    username: str
    role: str
    is_authenticated: bool = True
    user_id: int = None


# === ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ТОКЕНА ИЗ COOKIES ИЛИ HEADERS ===
def get_token_from_request(request: Request) -> Optional[str]:
    """
    Получает токен из Authorization header или из cookies
    """
    # Сначала проверяем заголовок Authorization
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]

    # Если нет в заголовке - проверяем cookies
    token = request.cookies.get("access_token")
    if token:
        return token

    return None


async def get_current_user_optional(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[AuthenticatedUser | AnonymousUser]:
    """
    Возвращает пользователя из токена или AnonymousUser.
    Разрешает анонимный доступ.
    """
    # Получаем токен из cookies или headers
    token = get_token_from_request(request)

    if not token:
        return AnonymousUser()

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
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> AuthenticatedUser:
    """
    ТРЕБУЕТ авторизации. Выбрасывает 401 если токена нет.
    """
    # Получаем токен из cookies или headers
    token = get_token_from_request(request)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
            headers={"WWW-Authenticate": "Bearer"},
        )

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


def require_reader(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    if user.role not in ["reader", "author", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется авторизация"
        )
    return user


def require_author(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    if user.role not in ["author", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль автора или администратора"
        )
    return user


def require_admin(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль администратора"
        )
    return user
