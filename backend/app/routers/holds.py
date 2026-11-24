# Why: Slot holds router for the 5-minute pre-booking reservation mechanism.
# Temporarily reserves a slot for a customer during checkout to prevent race conditions.

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import (
    BadRequestException,
    ConflictException,
    NotFoundException,
    ForbiddenException,
)
from app.db.session import get_db
from app.models import Service, Stylist, stylist_services, WorkingHours, TimeOff, Booking, SlotHold, User
from app.schemas.hold import HoldCreate, HoldOut

router = APIRouter(prefix="/holds", tags=["holds"])


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.post("", response_model=HoldOut, status_code=status.HTTP_201_CREATED)
async def create_slot_hold(
    payload: HoldCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a temporary 5-minute reservation on a slot for the authenticated user.
    Prevents other users from seeing or booking this slot during checkout.
    """
    now_utc = datetime.now(timezone.utc)
    start_ts = _ensure_utc(payload.start_ts)

    # 1. Start time must not be in the past
    if start_ts <= now_utc:
        raise BadRequestException(
            detail="Cannot hold a slot in the past",
            code="PAST_SLOT"
        )

    # 2. Verify Service
    srv_stmt = select(Service).where(Service.id == payload.service_id, Service.is_active.is_(True))
    service = (await db.execute(srv_stmt)).scalar_one_or_none()
    if not service:
        raise NotFoundException(detail="Service not found or inactive", code="SERVICE_NOT_FOUND")

    # 3. Verify Stylist
    st_stmt = select(Stylist).where(Stylist.id == payload.stylist_id, Stylist.is_active.is_(True))
    stylist = (await db.execute(st_stmt)).scalar_one_or_none()
    if not stylist:
        raise NotFoundException(detail="Stylist not found or inactive", code="STYLIST_NOT_FOUND")

    # 4. Verify Stylist offers Service
    map_stmt = select(stylist_services).where(
        stylist_services.c.stylist_id == payload.stylist_id,
        stylist_services.c.service_id == payload.service_id
    )
    if not (await db.execute(map_stmt)).first():
        raise BadRequestException(
            detail="The selected stylist does not offer this service",
            code="INVALID_STYLIST_SERVICE"
        )

    end_ts = start_ts + timedelta(minutes=service.duration_min)

    # 5. Shift boundary check
    wh_stmt = select(WorkingHours).where(
        WorkingHours.stylist_id == payload.stylist_id,
        WorkingHours.weekday == start_ts.weekday()
    )
    wh = (await db.execute(wh_stmt)).scalar_one_or_none()
    if not wh or start_ts.time() < wh.start_time or end_ts.time() > wh.end_time:
        raise BadRequestException(
            detail="Slot falls outside stylist working hours",
            code="OUTSIDE_WORKING_HOURS"
        )

    # 6. Time Off check
    to_stmt = select(TimeOff).where(
        TimeOff.stylist_id == payload.stylist_id,
        TimeOff.start_ts < end_ts,
        TimeOff.end_ts > start_ts
    )
    if (await db.execute(to_stmt)).scalar_one_or_none():
        raise ConflictException(
            detail="Stylist is on leave during this time",
            code="STYLIST_UNAVAILABLE"
        )

    # 7. Confirmed booking check
    bk_stmt = select(Booking).where(
        Booking.stylist_id == payload.stylist_id,
        Booking.status == "confirmed",
        Booking.start_ts < end_ts,
        Booking.end_ts > start_ts
    )
    if (await db.execute(bk_stmt)).scalar_one_or_none():
        raise ConflictException(
            detail="The selected time slot is already booked",
            code="SLOT_TAKEN"
        )

    # 8. Check if held by another user
    existing_hold_stmt = select(SlotHold).where(
        SlotHold.stylist_id == payload.stylist_id,
        SlotHold.expires_at > now_utc,
        SlotHold.start_ts < end_ts,
        SlotHold.end_ts > start_ts
    )
    existing_hold = (await db.execute(existing_hold_stmt)).scalar_one_or_none()
    if existing_hold:
        if existing_hold.user_id != current_user.id:
            raise ConflictException(
                detail="The selected time slot is temporarily on hold by another customer",
                code="SLOT_HELD"
            )
        # If already held by current user, extend the 5-minute expiry
        existing_hold.expires_at = now_utc + timedelta(minutes=5)
        await db.commit()
        await db.refresh(existing_hold)
        return existing_hold

    # 9. Create fresh 5-minute hold
    hold = SlotHold(
        user_id=current_user.id,
        stylist_id=payload.stylist_id,
        start_ts=start_ts,
        end_ts=end_ts,
        expires_at=now_utc + timedelta(minutes=5),
    )
    db.add(hold)
    await db.commit()
    await db.refresh(hold)
    return hold


@router.delete("/{hold_id}")
async def release_slot_hold(
    hold_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Releases an active hold before its 5-minute expiration so other users can immediately book it.
    """
    stmt = select(SlotHold).where(SlotHold.id == hold_id)
    hold = (await db.execute(stmt)).scalar_one_or_none()
    if not hold:
        raise NotFoundException(detail="Hold reservation not found", code="HOLD_NOT_FOUND")

    if hold.user_id != current_user.id and current_user.role != "admin":
        raise ForbiddenException(detail="Cannot release another user's hold", code="FORBIDDEN")

    await db.delete(hold)
    await db.commit()
    return {"detail": "Slot hold released successfully", "code": "HOLD_RELEASED"}

