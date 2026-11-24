# Why: APScheduler job sending 24-hour appointment reminder emails and notifications.
# Queries confirmed bookings in the [now+23h, now+25h] window (run hourly) to avoid
# sending duplicates while covering the full 24-hour look-ahead.

import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking, Notification
from app.services.notification_service import create_notification
from app.services.email_service import build_booking_reminder_content

logger = logging.getLogger("stylify.jobs.reminders")

REMINDER_HOURS_BEFORE = 24


async def send_24h_reminders(session: AsyncSession) -> int:
    """
    Finds all confirmed bookings whose start_ts falls between now+23h and now+25h
    and whose user has NOT already received a 'reminder_24h' notification for that booking.
    Sends in-app + email reminders. Runs hourly to cover the full look-ahead window.
    """
    now_utc = datetime.now(timezone.utc)
    window_start = now_utc + timedelta(hours=REMINDER_HOURS_BEFORE - 1)
    window_end = now_utc + timedelta(hours=REMINDER_HOURS_BEFORE + 1)

    # Fetch all confirmed bookings in the 24h window
    stmt = (
        select(Booking)
        .options(
            selectinload(Booking.service),
            selectinload(Booking.stylist),
            selectinload(Booking.user),
        )
        .where(
            Booking.status == "confirmed",
            Booking.start_ts >= window_start,
            Booking.start_ts < window_end,
        )
    )
    bookings = (await session.execute(stmt)).scalars().all()
    if not bookings:
        return 0

    count = 0
    for booking in bookings:
        # Skip if reminder already sent for this booking
        already_sent_stmt = select(Notification).where(
            Notification.booking_id == booking.id,
            Notification.type == "reminder_24h",
        )
        if (await session.execute(already_sent_stmt)).scalar_one_or_none():
            continue

        user = booking.user
        service_name = booking.service.name if booking.service else "Service"
        stylist_name = booking.stylist.name if booking.stylist else "Stylist"
        start_str = booking.start_ts.strftime("%Y-%m-%d %H:%M") if booking.start_ts else "N/A"

        subject, body = build_booking_reminder_content(
            customer_name=user.name,
            service_name=service_name,
            stylist_name=stylist_name,
            start_ts_str=start_str,
        )

        # Persist notification row; email is dispatched synchronously in the job context
        await create_notification(
            db=session,
            user_id=user.id,
            type="reminder_24h",
            message=body,
            booking_id=booking.id,
            to_email=user.email,
            email_subject=subject,
            background_tasks=None,  # sync dispatch inside scheduler, not via BackgroundTasks
        )

        from app.services.email_service import send_email_sync
        send_email_sync(to_email=user.email, subject=subject, body_text=body)

        count += 1

    if count:
        await session.commit()
        logger.info(f"Sent {count} 24-hour appointment reminder(s)")

    return count
