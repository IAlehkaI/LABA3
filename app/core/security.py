# app/core/security.py — ФИНАЛЬНАЯ ВЕРСИЯ (100% рабочая, ноябрь 2025)
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

# === НАСТРОЙКИ ===
SECRET_KEY = "super-secret-jwt-key-change-in-prod-2025"  # ← поменяй в .env потом
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 часа

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# === ПАРОЛИ ===
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# === JWT ===
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
# ЭТО ТО, ЧЕГО НЕ ХВАТАЛО!
class TokenData(BaseModel):
    username: str
    is_admin: bool = False

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        is_admin: bool = payload.get("is_admin", False)
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return TokenData(username=username, is_admin=is_admin)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_role(role: str = "admin"):
    def role_checker(user: TokenData = Depends(get_current_user)):
        if role == "admin" and not user.is_admin:
            raise HTTPException(status_code=403, detail="Недостаточно прав")
        return user
    return role_checker
