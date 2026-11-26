from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text, event
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

super_engine = (
    create_async_engine(
        settings.ALEMBIC_DATABASE_URL,
        echo=False,
        future=True,
        pool_size=5,
        max_overflow=2,
        pool_pre_ping=True,
    )
    if settings.ALEMBIC_DATABASE_URL
    else engine
)

SuperAsyncSessionLocal = (
    async_sessionmaker(
        bind=super_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    if settings.ALEMBIC_DATABASE_URL
    else AsyncSessionLocal
)

Base = declarative_base()

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Server-side super/owner DB sessiyasi (auth va SUPER_ADMIN operatsiyalari uchun, GUC ishlatmaydi)."""
    async with SuperAsyncSessionLocal() as session:
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
    - SUPER_ADMIN uchun server tomonidan SuperAsyncSessionLocal (owner/maktab_super) tanlanadi.
    - Oddiy tenantlar uchun AsyncSessionLocal (maktab_app) va faqat app.current_school_id o'rnatiladi.
    """
    if current_user.role == "SUPER_ADMIN":
        async with SuperAsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
        return

    school_id_str = str(current_user.school_id) if current_user.school_id else ""

    async with AsyncSessionLocal() as session:
        @event.listens_for(session.sync_session, "after_begin")
        def _set_tenant_ctx(sync_sess, transaction, connection):
            connection.execute(
                text("SELECT set_config('app.current_school_id', :sid, true)"),
                {"sid": school_id_str}
            )

        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
