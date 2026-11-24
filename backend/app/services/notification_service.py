# Why: Notification business service managing in-app alerts and asynchronous email dispatch.
# Persists notification rows to the database and schedules background email tasks.

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification
from app.services.email_service import send_email_sync


async def create_notification(
    db: AsyncSession,
    user_id: int,
    type: str,
    message: str,
    booking_id: int | None = None,
    channel: str = "in_app",
    to_email: str | None = None,
    email_subject: str | None = None,
    background_tasks: BackgroundTasks | None = None,
) -> Notification:
    """
    Creates an in-app notification DB row and asynchronously dispatches an email via BackgroundTasks.
    """
    notification = Notification(
        user_id=user_id,
        booking_id=booking_id,
        type=type,
        message=message,
        channel=channel,
        status="unread",
    )
    db.add(notification)
    await db.flush()

    # Trigger email delivery if recipient address and background runner are available
    if to_email and background_tasks:
        subject = email_subject or f"Notification from Stylify: {type.replace('_', ' ').title()}"
        background_tasks.add_task(
            send_email_sync,
            to_email=to_email,
            subject=subject,
            body_text=message,
        )

    return notification

