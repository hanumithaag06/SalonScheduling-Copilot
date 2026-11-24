# Why: Booking lifecycle router: creation, rescheduling, cancellation, and customer history.
# Uses get_current_user dependency and delegates business logic to booking_service.

from datetime import date, datetime, time, timezone
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Booking, User
from app.schemas.booking import BookingCreate, BookingReschedule, BookingOut
from app.services.booking_service import create_booking, reschedule_booking, cancel_booking

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
async def book_appointment(
    payload: BookingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a new confirmed booking. Validates operating hours, customer overlaps,
    max active appointments, and catches database exclusion violations (409 SLOT_TAKEN).
    """
    return await create_booking(payload=payload, user=current_user, db=db)


@router.put("/{booking_id}", response_model=BookingOut)
async def update_booking_time(
    booking_id: int,
    payload: BookingReschedule,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Reschedules an existing confirmed booking.
    Enforces a strict 2-hour minimum lead window before current start time.
    """
    return await reschedule_booking(booking_id=booking_id, payload=payload, user=current_user, db=db)


@router.post("/{booking_id}/cancel", response_model=BookingOut)
async def cancel_appointment(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancels a confirmed booking if within the permitted cancellation policy (>2 hours before start).
    """
    return await cancel_booking(booking_id=booking_id, user=current_user, db=db)


@router.get("/me", response_model=list[BookingOut])
async def get_my_bookings(
    status: str | None = Query(default=None, description="Filter by status (confirmed, cancelled, completed)"),
    start_date: date | None = Query(default=None, description="Filter bookings on or after date"),
    end_date: date | None = Query(default=None, description="Filter bookings on or before date"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the appointment history for the authenticated customer.
    Supports optional status and date range query parameters.
    """
    stmt = (
        select(Booking)
        .options(selectinload(Booking.service), selectinload(Booking.stylist))
        .where(Booking.user_id == current_user.id)
    )

    if status:
        stmt = stmt.where(Booking.status == status.lower())
    if start_date:
        start_bound = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        stmt = stmt.where(Booking.start_ts >= start_bound)
    if end_date:
        end_bound = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
        stmt = stmt.where(Booking.start_ts <= end_bound)

    stmt = stmt.order_by(Booking.start_ts.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

