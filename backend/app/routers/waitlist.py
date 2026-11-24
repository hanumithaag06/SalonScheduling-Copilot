# Why: Waitlist router exposing join, view, and claim endpoints.
# Customers can queue up for cancelled slots and claim an offered seat within 15 minutes.

from datetime import date
from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Waitlist, User
from app.schemas.waitlist import WaitlistCreate, WaitlistOut
from app.services.waitlist_service import join_waitlist, claim_waitlist_offer

router = APIRouter(prefix="/waitlist", tags=["waitlist"])


@router.post("", response_model=WaitlistOut, status_code=status.HTTP_201_CREATED)
async def join_waitlist_route(
    payload: WaitlistCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Adds the authenticated customer to the appointment waitlist.
    When a matching slot is freed by cancellation, they receive a 15-minute offer.
    """
    return await join_waitlist(
        service_id=payload.service_id,
        target_date=payload.date,
        time_pref=payload.time_pref,
        stylist_id=payload.stylist_id,
        user=current_user,
        db=db,
    )


@router.get("/me", response_model=list[WaitlistOut])
async def get_my_waitlist_entries(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns all waitlist entries for the authenticated customer, newest first."""
    stmt = (
        select(Waitlist)
        .where(Waitlist.user_id == current_user.id)
        .order_by(Waitlist.created_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return rows


@router.post("/{waitlist_id}/claim", response_model=WaitlistOut)
async def claim_offered_slot(
    waitlist_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Claims an offered waitlist slot within the 15-minute window, creating a confirmed booking.
    If the window has expired, cascades the slot to the next eligible customer.
    Returns the updated waitlist entry (status='claimed').
    """
    from app.core.errors import NotFoundException, ForbiddenException

    # Fetch waitlist entry for the response — the booking is created internally
    stmt = select(Waitlist).where(Waitlist.id == waitlist_id)
    entry = (await db.execute(stmt)).scalar_one_or_none()
    if not entry:
        raise NotFoundException(detail="Waitlist entry not found", code="WAITLIST_ENTRY_NOT_FOUND")
    if entry.user_id != current_user.id and current_user.role != "admin":
        raise ForbiddenException(detail="Cannot claim another user's offer", code="FORBIDDEN")

    await claim_waitlist_offer(
        waitlist_id=waitlist_id,
        user=current_user,
        db=db,
        background_tasks=background_tasks,
    )

    # Refresh the entry and return it in 'claimed' state
    await db.refresh(entry)
    return entry
