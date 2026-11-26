from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text, event
from core.config import settings
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
        @event.listens_for(session.sync_session, "after_begin")
        def _set_super_admin_ctx(sync_sess, transaction, connection):
            connection.execute(
                text(
                    "SELECT set_config('app.is_super_admin', 'on', true), "
                    "set_config('app.current_role', 'SUPER_ADMIN', true)"
                )
            )

        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


from core.rbac import CurrentUser, get_current_user


async def get_tenant_db(
    current_user: CurrentUser = Depends(get_current_user),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Multi-tenant RLS sessiyasi:
    Har bir tranzaksiya boshida (after_begin, jumladan commitdan keyin ham)
    PostgreSQL ga app.current_school_id va app.is_super_admin ni uzatadi.
    """
    is_super_admin = "on" if current_user.role == "SUPER_ADMIN" else "off"
    role_str = str(current_user.role or "")
    school_id_str = str(current_user.school_id) if current_user.school_id else ""

    async with AsyncSessionLocal() as session:
        @event.listens_for(session.sync_session, "after_begin")
        def _set_tenant_ctx(sync_sess, transaction, connection):
            connection.execute(
                text(
                    "SELECT set_config('app.is_super_admin', :sa, true), "
                    "set_config('app.current_role', :role, true), "
                    "set_config('app.current_school_id', :sid, true)"
                ),
                {"sa": is_super_admin, "role": role_str, "sid": school_id_str}
            )

        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
