# Why: Endpoints for stylist working hours and time off (vacations, holidays).
# Allows admins to manage schedules and customers/engine to view stylist shifts.

from fastapi import APIRouter, Depends, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.core.errors import NotFoundException
from app.db.session import get_db
from app.models import WorkingHours, TimeOff, Stylist, User
from app.schemas.schedule import (
    WorkingHoursCreate, WorkingHoursOut,
    TimeOffCreate, TimeOffOut
)

router = APIRouter(prefix="/stylists", tags=["schedule"])


# ──────────────────────────────────────────────────────────────
# Working Hours
# ──────────────────────────────────────────────────────────────

@router.get("/{stylist_id}/working-hours", response_model=list[WorkingHoursOut])
async def list_working_hours(stylist_id: int, db: AsyncSession = Depends(get_db)):
    """List weekly shifts for a stylist, ordered Mon (0) to Sun (6)."""
    stmt = (
        select(WorkingHours)
        .where(WorkingHours.stylist_id == stylist_id)
        .order_by(WorkingHours.weekday)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/{stylist_id}/working-hours", response_model=WorkingHoursOut, status_code=status.HTTP_201_CREATED)
async def set_working_hours(
    stylist_id: int,
    payload: WorkingHoursCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: Set or update working hours for a stylist on a specific weekday."""
    # Verify stylist exists
    st_stmt = select(Stylist).where(Stylist.id == stylist_id)
    if not (await db.execute(st_stmt)).scalar_one_or_none():
        raise NotFoundException(detail="Stylist not found", code="STYLIST_NOT_FOUND")

    # If shift for this weekday already exists, update it; otherwise create new
    existing_stmt = select(WorkingHours).where(
        WorkingHours.stylist_id == stylist_id,
        WorkingHours.weekday == payload.weekday
    )
    wh = (await db.execute(existing_stmt)).scalar_one_or_none()

    if wh:
        wh.start_time = payload.start_time
        wh.end_time = payload.end_time
    else:
        wh = WorkingHours(
            stylist_id=stylist_id,
            weekday=payload.weekday,
            start_time=payload.start_time,
            end_time=payload.end_time,
        )
        db.add(wh)

    await db.commit()
    await db.refresh(wh)
    return wh


@router.delete("/{stylist_id}/working-hours/{wh_id}")
async def delete_working_hours(
    stylist_id: int,
    wh_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: Remove a working hours entry (stylist day off)."""
    stmt = select(WorkingHours).where(
        WorkingHours.id == wh_id,
        WorkingHours.stylist_id == stylist_id
    )
    wh = (await db.execute(stmt)).scalar_one_or_none()
    if not wh:
        raise NotFoundException(detail="Working hours entry not found", code="WORKING_HOURS_NOT_FOUND")

    await db.delete(wh)
    await db.commit()
    return {"detail": "Working hours entry removed", "code": "WORKING_HOURS_DELETED"}


# ──────────────────────────────────────────────────────────────
# Time Off
# ──────────────────────────────────────────────────────────────

@router.get("/{stylist_id}/time-off", response_model=list[TimeOffOut])
async def list_time_off(stylist_id: int, db: AsyncSession = Depends(get_db)):
    """List scheduled time-off / leaves for a stylist."""
    stmt = (
        select(TimeOff)
        .where(TimeOff.stylist_id == stylist_id)
        .order_by(TimeOff.start_ts)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/{stylist_id}/time-off", response_model=TimeOffOut, status_code=status.HTTP_201_CREATED)
async def create_time_off(
    stylist_id: int,
    payload: TimeOffCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: Record stylist time-off or vacation."""
    st_stmt = select(Stylist).where(Stylist.id == stylist_id)
    if not (await db.execute(st_stmt)).scalar_one_or_none():
        raise NotFoundException(detail="Stylist not found", code="STYLIST_NOT_FOUND")

    to = TimeOff(
        stylist_id=stylist_id,
        start_ts=payload.start_ts,
        end_ts=payload.end_ts,
        reason=payload.reason,
    )
    db.add(to)
    await db.commit()
    await db.refresh(to)
    return to


@router.delete("/{stylist_id}/time-off/{to_id}")
async def delete_time_off(
    stylist_id: int,
    to_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: Cancel a time-off block."""
    stmt = select(TimeOff).where(
        TimeOff.id == to_id,
        TimeOff.stylist_id == stylist_id
    )
    to = (await db.execute(stmt)).scalar_one_or_none()
    if not to:
        raise NotFoundException(detail="Time-off entry not found", code="TIME_OFF_NOT_FOUND")

    await db.delete(to)
    await db.commit()
    return {"detail": "Time-off entry deleted", "code": "TIME_OFF_DELETED"}

