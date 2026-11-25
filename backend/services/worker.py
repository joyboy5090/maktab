"""
Mustaqil background worker (Docker Compose 'worker' xizmati uchun).
Navbatdagi 'pending' dars jadvali vazifalarini olib, ProcessPoolExecutor da bajaradi.
"""
import asyncio
import logging
from sqlalchemy import select, text, event
import database.connection as db_conn
from database.models import TimetableJob
from services.timetable_service import TimetableService

logger = logging.getLogger("maktab_worker")


async def run_worker_loop(poll_interval: float = 2.0) -> None:
    logger.info("Maktab Timetable Worker ishga tushdi...")
    while True:
        try:
            pending_jobs = []
            async with db_conn.AsyncSessionLocal() as db:
                @event.listens_for(db.sync_session, "after_begin")
                def _set_sa(sync_sess, transaction, connection):
                    connection.execute(text("SELECT set_config('app.is_super_admin', 'on', true)"))

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
        except Exception as exc:
            logger.error(f"Worker xatosi: {exc}")

        await asyncio.sleep(poll_interval)


if __name__ == "__main__":
    asyncio.run(run_worker_loop())
