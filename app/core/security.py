# app/core/security.py — ФИНАЛЬНАЯ ВЕРСИЯ С АНОНИМНЫМИ ПОЛЬЗОВАТЕЛЯМИ
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

# HTTPBearer вместо OAuth2PasswordBearer (не выбрасывает 401 автоматически)
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
class TokenData(BaseModel):
    username: str
    is_admin: bool = False
    role: str = "user"


class AnonymousUser(BaseModel):
    username: str = "anonymous"
    is_admin: bool = False
    role: str = "anonymous"


# === ПОЛУЧЕНИЕ ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ (С ПОДДЕРЖКОЙ АНОНИМОВ) ===
async def get_current_user_optional(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> TokenData | AnonymousUser:
    """
    Возвращает пользователя из токена или анонимного пользователя.
    НЕ выбрасывает ошибку 401 - разрешает анонимный доступ.
    """
    if not credentials:
        return AnonymousUser()

    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        return AnonymousUser()

    username = payload.get("sub")
    is_admin = payload.get("is_admin", False)

    if not username:
        return AnonymousUser()

    return TokenData(
        username=username,
        is_admin=is_admin,
        role="admin" if is_admin else "user"
    )


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """
    ТРЕБУЕТ авторизации. Выбрасывает 401 если токена нет.
    Используйте для защищённых эндпоинтов.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("sub")
    is_admin = payload.get("is_admin", False)

    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenData(
        username=username,
        is_admin=is_admin,
        role="admin" if is_admin else "user"
    )


# === ПРОВЕРКА РОЛЕЙ ===
def require_admin(user: TokenData = Depends(get_current_user)) -> TokenData:
    """Требует роль администратора"""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав. Требуется роль администратора."
        )
    return user


def require_authenticated(user: TokenData = Depends(get_current_user)) -> TokenData:
    """Требует любого авторизованного пользователя (не анонима)"""
    return user
