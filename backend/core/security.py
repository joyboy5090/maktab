from datetime import datetime, timedelta, timezone
from typing import Any, Union, Optional
from jose import jwt
import bcrypt
from core.config import settings

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    # bcrypt maksimal 72 baytni qabul qiladi
    pw_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")

def create_access_token(
    subject: Union[str, Any],
    school_id: Optional[str] = None,
    role: str = "TEACHER",
    email: Optional[str] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": str(subject),
        "email": email or (str(subject) if "@" in str(subject) else ""),
        "school_id": str(school_id) if school_id else None,
        "role": role,
        "exp": expire
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(
    subject: Union[str, Any],
    school_id: Optional[str] = None,
    role: str = "TEACHER",
    email: Optional[str] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """7 kunlik refresh token yaratadi"""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "sub": str(subject),
        "email": email or (str(subject) if "@" in str(subject) else ""),
        "school_id": str(school_id) if school_id else None,
        "role": role,
        "type": "refresh",
        "exp": expire
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> dict:
    """Tokenni dekod qiladi va payload qaytaradi"""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
