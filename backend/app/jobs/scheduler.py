# Why: APScheduler setup for background asynchronous maintenance jobs.
# Manages the lifecycle of periodic tasks such as expired hold purging,
# 24-hour appointment reminders, and waitlist offer cascading.

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.db.session import AsyncSessionLocal
from app.jobs.cleanup_holds import delete_expired_holds

logger = logging.getLogger("stylify.scheduler")
scheduler = AsyncIOScheduler()


async def scheduled_cleanup_job():
    """Runs periodically to purge expired slot_holds rows from the database."""
    try:
        async with AsyncSessionLocal() as session:
            count = await delete_expired_holds(session)
            if count > 0:
                logger.info(f"Purged {count} expired slot hold(s)")
    except Exception as e:
        logger.error(f"Error executing expired holds cleanup job: {e}")


async def scheduled_reminder_job():
    """Sends 24-hour reminder emails for upcoming confirmed appointments."""
    try:
        from app.jobs.reminder_job import send_24h_reminders
        async with AsyncSessionLocal() as session:
            await send_24h_reminders(session)
    except Exception as e:
        logger.error(f"Error executing 24h reminder job: {e}")


async def scheduled_waitlist_cascade_job():
    """Expires overdue waitlist offers and cascades slots to the next eligible customer."""
    try:
        from app.jobs.waitlist_job import expire_and_cascade_waitlist_offers
        async with AsyncSessionLocal() as session:
            await expire_and_cascade_waitlist_offers(session)
    except Exception as e:
        logger.error(f"Error executing waitlist cascade job: {e}")


def start_scheduler():
    """Configures and starts the background task scheduler."""
    if not scheduler.running:
        scheduler.add_job(
            scheduled_cleanup_job,
            trigger="interval",
            minutes=1,
            id="cleanup_expired_holds",
            replace_existing=True,
        )
        scheduler.add_job(
            scheduled_reminder_job,
            trigger="interval",
            hours=1,
            id="send_24h_reminders",
            replace_existing=True,
        )
        scheduler.add_job(
            scheduled_waitlist_cascade_job,
            trigger="interval",
            minutes=1,
            id="expire_waitlist_offers",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("APScheduler background jobs started")


def stop_scheduler():
    """Gracefully shuts down the background scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler background jobs stopped")

