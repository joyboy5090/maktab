from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from core.config import settings
from core.rbac import CurrentUser, get_current_user
from fastapi import Depends

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Oddiy DB sessiya (auth yoki super-admin operatsiyalari uchun)"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def get_tenant_db(
    current_user: CurrentUser = Depends(get_current_user),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Multi-tenant RLS sessiyasi:
    PostgreSQL ga joriy maktabning ID sini uzatadi.
    Shu orqali RLS siyosatlari avtomatik filtrlaydi.
    """
    async with AsyncSessionLocal() as session:
        try:
            if current_user.school_id:
                # PostgreSQL RLS: set_config parameterized query xavfsiz va $1 bind parametrlarini qo'llab-quvvatlaydi
                await session.execute(
                    text("SELECT set_config('app.current_school_id', :sid, true)"),
                    {"sid": str(current_user.school_id)}
                )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
