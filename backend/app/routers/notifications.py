# Why: Notification router exposing GET /notifications for in-app alerts.
# Allows customers to view their personal notification history and mark items as read.

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Notification, User
from app.schemas.notification import NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
async def get_my_notifications(
    unread_only: bool = Query(default=False, description="Return only unread notifications"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum number of notifications"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the authenticated customer's notification inbox sorted newest-first.
    Supports filtering to unread items only and a configurable page size.
    """
    stmt = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    if unread_only:
        stmt = stmt.where(Notification.status == "unread")

    rows = (await db.execute(stmt)).scalars().all()
    return rows


@router.post("/{notification_id}/read", response_model=NotificationOut)
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Marks a specific notification as 'read'.
    Only the notification owner may mark it.
    """
    from app.core.errors import NotFoundException, ForbiddenException

    stmt = select(Notification).where(Notification.id == notification_id)
    notif = (await db.execute(stmt)).scalar_one_or_none()
    if not notif:
        raise NotFoundException(detail="Notification not found", code="NOTIFICATION_NOT_FOUND")
    if notif.user_id != current_user.id:
        raise ForbiddenException(detail="Cannot mark another user's notification", code="FORBIDDEN")

    notif.status = "read"
    await db.commit()
    await db.refresh(notif)
    return notif
