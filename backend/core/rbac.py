from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from pydantic import BaseModel
from core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

class CurrentUser(BaseModel):
    id: str
    email: str
    role: str  # SUPER_ADMIN, SCHOOL_ADMIN, TEACHER
    school_id: Optional[str] = None

async def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Autentifikatsiya ma'lumotlari yaroqsiz yoki eskirgan",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: str = payload.get("sub")
        school_id: Optional[str] = payload.get("school_id")
        role: str = payload.get("role", "TEACHER")
        if user_id is None:
            raise credentials_exception
        return CurrentUser(id=user_id, email=payload.get("email", ""), role=role, school_id=school_id)
    except jwt.PyJWTError:
        raise credentials_exception

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
