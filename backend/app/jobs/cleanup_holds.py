# Why: Periodic database cleanup job for expired slot holds.
# Only deletes rows whose expires_at is in the past; read-time filtering handles freshness.

from datetime import datetime, timezone
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import SlotHold


async def delete_expired_holds(session: AsyncSession) -> int:
    """
    Deletes all slot_holds whose expires_at is past the current UTC time.
    Returns the count of purged hold records.
    """
    now_utc = datetime.now(timezone.utc)
    stmt = delete(SlotHold).where(SlotHold.expires_at <= now_utc)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount or 0
