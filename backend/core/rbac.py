import uuid
from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from core.config import settings
from database.connection import get_db_session
from database.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

class CurrentUser(BaseModel):
    id: str
    email: str
    role: str  # SUPER_ADMIN, SCHOOL_ADMIN, TEACHER
    school_id: Optional[str] = None

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> CurrentUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Autentifikatsiya ma'lumotlari yaroqsiz yoki eskirgan",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: Optional[str] = payload.get("sub")
        role: Optional[str] = payload.get("role")
        if not user_id or not role or role not in ("SUPER_ADMIN", "SCHOOL_ADMIN", "TEACHER"):
            raise credentials_exception
        uuid.UUID(str(user_id))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise credentials_exception

    user = await db.get(User, str(user_id))
    if not user or not user.is_active:
        raise credentials_exception

    return CurrentUser(
        id=user.id,
        email=user.email,
        role=user.role,
        school_id=user.school_id,
    )

class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Ushbu amalni bajarish uchun sizda yetarli ruxsat mavjud emas (RBAC cheklovi)"
            )
        return user

# Tezkor RBAC ruxsat tekshiruvlari
require_super_admin = RoleChecker(["SUPER_ADMIN"])
require_school_admin = RoleChecker(["SUPER_ADMIN", "SCHOOL_ADMIN"])
require_any_authenticated = RoleChecker(["SUPER_ADMIN", "SCHOOL_ADMIN", "TEACHER"])
