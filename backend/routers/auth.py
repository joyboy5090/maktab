from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.security import verify_password, create_access_token, create_refresh_token, decode_token, get_password_hash
from core.rbac import CurrentUser, get_current_user, require_school_admin
from core.limiter import limiter
from database.connection import get_db_session
from database.models import User, School
from schemas.schemas import LoginRequest, TokenResponse, RefreshTokenRequest, SchoolResponse, SchoolUpdate

router = APIRouter(prefix="/auth", tags=["Autentifikatsiya & RBAC"])

# Timing attack himoyasi uchun soxta bcrypt xesh
_DUMMY_PASSWORD_HASH = get_password_hash("dummy-timing-protection-password")

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    req: LoginRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Haqiqiy foydalanuvchi ma'lumotlar bazasidan tekshiriladi.
    Muvaffaqiyatli kirishda access va refresh token qaytariladi.
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
        email=user.email
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user.role,
        school_id=user.school_id,
        email=user.email
    )

@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
async def refresh_access_token(
    request: Request,
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Refresh token yordamida yangi access_token va refresh_token olish
    """
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Yaroqsiz token turi (refresh token kutilgan)"
            )
        user_id = payload.get("sub")
        user = await db.get(User, user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Foydalanuvchi topilmadi yoki hisob faol emas"
            )

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
            email=user.email
        )
        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            role=user.role,
            school_id=user.school_id,
            email=user.email
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token yaroqsiz yoki muddati o'tgan"
        )

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
