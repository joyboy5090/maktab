"""
Mustaqil background worker (Docker Compose 'worker' xizmati uchun).
Navbatdagi 'pending' dars jadvali vazifalarini olib, ProcessPoolExecutor da bajaradi.
"""
import asyncio
import logging
from sqlalchemy import select
import database.connection as db_conn
from database.models import TimetableJob
from services.timetable_service import TimetableService

logger = logging.getLogger("maktab_worker")


async def process_pending_jobs_once() -> int:
    """
    SuperAsyncSessionLocal (owner/maktab_super) orqali navbatdagi 'pending' vazifalarni o'qiydi
    va har birini shu maktabning school_id konteksti bilan maktab_app sessiyasida bajaradi.
    """
    async with db_conn.SuperAsyncSessionLocal() as db:
        res = await db.execute(
            select(TimetableJob)
            .where(TimetableJob.status == "pending")
            .order_by(TimetableJob.created_at.asc())
            .limit(5)
        )
        pending_jobs = [(j.id, j.school_id, j.term) for j in res.scalars().all()]

    for job_id, school_id, term in pending_jobs:
        await TimetableService.execute_job_in_background(
            job_id=job_id,
            school_id=school_id,
            term=term,
        )
    return len(pending_jobs)


async def run_worker_loop(poll_interval: float = 2.0) -> None:
    logger.info("Maktab Timetable Worker ishga tushdi...")
    while True:
        try:
            await process_pending_jobs_once()
        except Exception as exc:
            logger.error(f"Worker xatosi: {exc}")

        await asyncio.sleep(poll_interval)


if __name__ == "__main__":
    asyncio.run(run_worker_loop())
