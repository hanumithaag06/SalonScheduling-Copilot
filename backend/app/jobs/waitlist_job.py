# Why: APScheduler job periodically expiring stale 'offered' waitlist entries
# and cascading the freed appointment slot to the next eligible customer.

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.waitlist_service import expire_and_cascade_offers

logger = logging.getLogger("stylify.jobs.waitlist")


async def expire_and_cascade_waitlist_offers(session: AsyncSession) -> int:
    """
    Finds all 'offered' waitlist entries whose 15-minute claim window has passed
    and cascades the freed slot to the next matching customer. Runs every minute.
    """
    count = await expire_and_cascade_offers(db=session, background_tasks=None)
    if count:
        logger.info(f"Expired and cascaded {count} waitlist offer(s)")
    return count
