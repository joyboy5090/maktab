from datetime import datetime, timedelta, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from core.config import settings
from core.security import verify_password, create_access_token, create_refresh_token, decode_token, get_password_hash
from core.rbac import CurrentUser, get_current_user, require_school_admin
from core.limiter import limiter
from database.connection import get_db_session
from database.models import User, School, RefreshToken
from schemas.schemas import LoginRequest, TokenResponse, SchoolResponse, SchoolUpdate

router = APIRouter(prefix="/auth", tags=["Autentifikatsiya & RBAC"])

REFRESH_COOKIE_NAME = "refresh_token"

# Timing attack himoyasi uchun soxta bcrypt xesh
_DUMMY_PASSWORD_HASH = get_password_hash("dummy-timing-protection-password")


def _is_prod_cookie() -> bool:
    return settings.ENVIRONMENT.lower() == "production"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=_is_prod_cookie(),
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=_is_prod_cookie(),
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    req: LoginRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Haqiqiy foydalanuvchi ma'lumotlar bazasidan tekshiriladi.
    Muvaffaqiyatli kirishda JSON da access_token, HttpOnly cookie da esa jti li refresh_token qaytariladi.
    Rate limit: 5 urinish / 1 daqiqa.
    """
    query = select(User).where(User.email == req.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    password_hash_to_check = user.password_hash if user else _DUMMY_PASSWORD_HASH
    password_valid = verify_password(req.password, password_hash_to_check)

    if not user or not user.is_active or not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email yoki parol noto'g'ri"
        )

    now = datetime.now(timezone.utc)
    jti = str(uuid.uuid4())
    db.add(
        RefreshToken(
            id=jti,
            user_id=user.id,
            expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    await db.commit()

    access_token = create_access_token(
        subject=user.id,
        school_id=user.school_id,
        role=user.role,
        email=user.email
    )
    refresh_token = create_refresh_token(
        subject=user.id,
        school_id=user.school_id,
        role=user.role,
        email=user.email,
        jti=jti,
    )
    _set_refresh_cookie(response, refresh_token)

    return TokenResponse(
        access_token=access_token,
        role=user.role,
        school_id=user.school_id,
        email=user.email
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
async def refresh_access_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session)
):
    """
    HttpOnly cookie dagi refresh tokenni rotatsiya qilib yangi access_token va refresh cookie qaytaradi.
    Bekor qilingan (revoked) token qayta ishlatilsa, shu foydalanuvchining barcha refresh tokenlari bekor qilinadi.
    """
    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token cookie topilmadi"
        )

    try:
        payload = decode_token(raw_refresh)
    except Exception:
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token yaroqsiz yoki muddati o'tgan"
        )

    if payload.get("type") != "refresh":
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yaroqsiz token turi (refresh token kutilgan)"
        )

    jti = payload.get("jti")
    user_id = payload.get("sub")
    if not jti or not user_id:
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token ma'lumotlari to'liq emas"
        )

    db_token = await db.get(RefreshToken, jti)
    if not db_token:
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token bazada topilmadi"
        )

    now = datetime.now(timezone.utc)

    # Reuse detection: revoked token qayta ishlatilsa, foydalanuvchining barcha tokenlarini bekor qilamiz
    if db_token.revoked_at is not None:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == db_token.user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await db.commit()
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bekor qilingan refresh token qayta ishlatildi; barcha sessiyalar yopildi"
        )

    expires_at = db_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token muddati tugagan"
        )

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Foydalanuvchi topilmadi yoki hisob faol emas"
        )

    # Rotatsiya: eski tokenni bekor qilib, yangisini yaratamiz
    new_jti = str(uuid.uuid4())
    db_token.revoked_at = now
    db_token.replaced_by = new_jti
    db.add(
        RefreshToken(
            id=new_jti,
            user_id=user.id,
            expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    await db.commit()

    new_access = create_access_token(
        subject=user.id,
        school_id=user.school_id,
        role=user.role,
        email=user.email
    )
    new_refresh = create_refresh_token(
        subject=user.id,
        school_id=user.school_id,
        role=user.role,
        email=user.email,
        jti=new_jti,
    )
    _set_refresh_cookie(response, new_refresh)

    return TokenResponse(
        access_token=new_access,
        role=user.role,
        school_id=user.school_id,
        email=user.email
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Joriy refresh tokenni bazada bekor qiladi va refresh_token cookie ni o'chiradi.
    """
    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_refresh:
        try:
            payload = decode_token(raw_refresh)
            jti = payload.get("jti")
            if jti:
                db_token = await db.get(RefreshToken, jti)
                if db_token and db_token.revoked_at is None:
                    db_token.revoked_at = datetime.now(timezone.utc)
                    await db.commit()
        except Exception:
            pass

    _clear_refresh_cookie(response)
    return {"success": True, "message": "Tizimdan muvaffaqiyatli chiqildi"}

@router.get("/me")
async def get_my_profile(current_user: CurrentUser = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "school_id": current_user.school_id
    }

@router.get("/school")
async def get_my_school(
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(get_current_user)
):
    if not current_user.school_id:
        raise HTTPException(status_code=400, detail="Maktab biriktirilmagan")
    school = await db.get(School, current_user.school_id)
    if not school:
        raise HTTPException(status_code=404, detail="Maktab topilmadi")
    return {
        "id": school.id,
        "name": school.name,
        "slug": school.slug,
        "subdomain": school.subdomain,
        "email": school.email,
        "phone": school.phone,
        "address": school.address,
        "is_active": school.is_active,
    }

@router.put("/school")
async def update_my_school(
    data: SchoolUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(require_school_admin)
):
    if not current_user.school_id:
        raise HTTPException(status_code=400, detail="Maktab biriktirilmagan")
    school = await db.get(School, current_user.school_id)
    if not school:
        raise HTTPException(status_code=404, detail="Maktab topilmadi")

    if data.name is not None:
        school.name = data.name
    if data.email is not None:
        school.email = data.email
    if data.phone is not None:
        school.phone = data.phone
    if data.address is not None:
        school.address = data.address

    await db.commit()
    await db.refresh(school)
    return {
        "id": school.id,
        "name": school.name,
        "slug": school.slug,
        "subdomain": school.subdomain,
        "email": school.email,
        "phone": school.phone,
        "address": school.address,
        "is_active": school.is_active,
    }
