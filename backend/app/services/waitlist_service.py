# Why: Salon appointment waitlist business logic and cascading offer management.
# Automatically offers cancelled slots to the earliest matching client for 15 minutes,
# and cascades to the next eligible client upon expiration.

from datetime import date, datetime, timedelta, timezone
import logging
from fastapi import BackgroundTasks
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    BadRequestException,
    ConflictException,
    NotFoundException,
    ForbiddenException,
)
from app.engine.waitlist_engine import (
    WaitlistCandidate,
    select_next_waitlist_candidate,
    compute_offer_expiration,
    is_offer_expired,
)
from app.models import Waitlist, Service, Stylist, stylist_services, Booking, User
from app.services.notification_service import create_notification
from app.services.email_service import (
    build_booking_confirmation_content,
    build_waitlist_offer_content,
)

logger = logging.getLogger("stylify.waitlist")


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def join_waitlist(
    service_id: int,
    target_date: date,
    time_pref: str,
    stylist_id: int | None,
    user: User,
    db: AsyncSession,
) -> Waitlist:
    """
    Registers a customer onto the waitlist for a specific date, service, and time preference.
    Guards against duplicate active entries and past dates.
    """
    now_date = datetime.now(timezone.utc).date()
    if target_date < now_date:
        raise BadRequestException(
            detail="Cannot join waitlist for a past date",
            code="PAST_DATE",
        )

    # 1. Validate service
    srv_stmt = select(Service).where(Service.id == service_id, Service.is_active.is_(True))
    service = (await db.execute(srv_stmt)).scalar_one_or_none()
    if not service:
        raise NotFoundException(detail="Service not found or inactive", code="SERVICE_NOT_FOUND")

    # 2. Validate stylist if provided
    if stylist_id is not None:
        st_stmt = (
            select(Stylist)
            .join(stylist_services, Stylist.id == stylist_services.c.stylist_id)
            .where(
                Stylist.id == stylist_id,
                stylist_services.c.service_id == service_id,
                Stylist.is_active.is_(True),
            )
        )
        stylist = (await db.execute(st_stmt)).scalar_one_or_none()
        if not stylist:
            raise BadRequestException(
                detail="Stylist not found or does not offer this service",
                code="STYLIST_UNAVAILABLE",
            )

    # 3. Check for existing active/waiting entry
    existing_stmt = select(Waitlist).where(
        Waitlist.user_id == user.id,
        Waitlist.service_id == service_id,
        Waitlist.date == target_date,
        Waitlist.status.in_(["waiting", "offered"]),
    )
    if (await db.execute(existing_stmt)).scalar_one_or_none():
        raise ConflictException(
            detail="You are already on the waitlist for this service and date",
            code="ALREADY_ON_WAITLIST",
        )

    # 4. Insert waitlist entry
    entry = Waitlist(
        user_id=user.id,
        service_id=service_id,
        stylist_id=stylist_id,
        date=target_date,
        time_pref=time_pref.lower(),
        status="waiting",
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def offer_vacated_slot(
    service_id: int,
    stylist_id: int,
    slot_start: datetime,
    db: AsyncSession,
    background_tasks: BackgroundTasks | None = None,
) -> Waitlist | None:
    """
    Searches for the earliest eligible waitlisted customer and grants them a 15-minute claim offer.
    Called automatically when an appointment is cancelled or an offer expires.
    """
    now_utc = datetime.now(timezone.utc)
    slot_start = _ensure_utc(slot_start)

    # 1. Fetch all waiting entries for this service and date
    stmt = (
        select(Waitlist)
        .options(selectinload(Waitlist.user), selectinload(Waitlist.service), selectinload(Waitlist.stylist))
        .where(
            Waitlist.service_id == service_id,
            Waitlist.date == slot_start.date(),
            Waitlist.status == "waiting",
        )
        .order_by(Waitlist.created_at.asc(), Waitlist.id.asc())
    )
    records = (await db.execute(stmt)).scalars().all()
    if not records:
        return None

    # 2. Build candidates for pure selector
    candidates = [
        WaitlistCandidate(
            id=r.id,
            user_id=r.user_id,
            service_id=r.service_id,
            stylist_id=r.stylist_id,
            date=r.date,
            time_pref=r.time_pref,
            created_at=_ensure_utc(r.created_at),
        )
        for r in records
    ]

    selected_candidate = select_next_waitlist_candidate(
        candidates=candidates,
        slot_start=slot_start,
        slot_stylist_id=stylist_id,
        service_id=service_id,
    )
    if not selected_candidate:
        return None

    # 3. Retrieve and update matching entry
    matching_entry = next(r for r in records if r.id == selected_candidate.id)
    expiry = compute_offer_expiration(now_utc, window_minutes=15)

    matching_entry.status = "offered"
    matching_entry.offered_slot_start = slot_start
    matching_entry.offer_expires_at = expiry
    # Ensure stylist_id is bound if candidate selected any stylist
    if matching_entry.stylist_id is None:
        matching_entry.stylist_id = stylist_id

    # 4. Fetch details for notification
    user_obj = matching_entry.user
    srv_name = matching_entry.service.name if matching_entry.service else "Salon Service"
    st_name = matching_entry.stylist.name if matching_entry.stylist else "Salon Stylist"

    # 5. Send notification and email
    subject, body = build_waitlist_offer_content(
        customer_name=user_obj.name,
        service_name=srv_name,
        stylist_name=st_name,
        slot_start_str=slot_start.strftime("%Y-%m-%d %H:%M"),
        expires_at_str=expiry.strftime("%H:%M"),
        claim_url=f"/waitlist/{matching_entry.id}/claim",
    )

    await create_notification(
        db=db,
        user_id=user_obj.id,
        type="waitlist_offer",
        message=body,
        to_email=user_obj.email,
        email_subject=subject,
        background_tasks=background_tasks,
    )

    await db.commit()
    await db.refresh(matching_entry)
    logger.info(
        f"Offered vacated slot {slot_start.isoformat()} to waitlist entry #{matching_entry.id} (user {user_obj.id})"
    )
    return matching_entry


async def claim_waitlist_offer(
    waitlist_id: int,
    user: User,
    db: AsyncSession,
    background_tasks: BackgroundTasks | None = None,
) -> Booking:
    """
    Converts an offered waitlist entry into a confirmed booking if claimed within 15 minutes.
    If the offer has expired, it cascades immediately to the next waiting customer.
    """
    now_utc = datetime.now(timezone.utc)

    stmt = (
        select(Waitlist)
        .options(
            selectinload(Waitlist.service),
            selectinload(Waitlist.stylist),
            selectinload(Waitlist.user),
        )
        .where(Waitlist.id == waitlist_id)
    )
    entry = (await db.execute(stmt)).scalar_one_or_none()
    if not entry:
        raise NotFoundException(detail="Waitlist entry not found", code="WAITLIST_ENTRY_NOT_FOUND")

    if entry.user_id != user.id and user.role != "admin":
        raise ForbiddenException(detail="Cannot claim another user's waitlist offer", code="FORBIDDEN")

    if entry.status != "offered":
        raise BadRequestException(
            detail=f"Waitlist entry is not in 'offered' status (current: {entry.status})",
            code="INVALID_WAITLIST_STATUS",
        )

    # Check 15-minute claim window expiry
    if is_offer_expired(entry.offer_expires_at, now_utc):
        entry.status = "expired"
        await db.commit()

        # Cascade immediately to the next person in line
        if entry.offered_slot_start and entry.stylist_id:
            await offer_vacated_slot(
                service_id=entry.service_id,
                stylist_id=entry.stylist_id,
                slot_start=entry.offered_slot_start,
                db=db,
                background_tasks=background_tasks,
            )

        raise ConflictException(
            detail="The 15-minute offer window for this slot has expired",
            code="OFFER_EXPIRED",
        )

    # Convert offer into a confirmed booking
    start_ts = _ensure_utc(entry.offered_slot_start)
    duration_min = entry.service.duration_min if entry.service else 30
    end_ts = start_ts + timedelta(minutes=duration_min)

    booking = Booking(
        user_id=user.id,
        service_id=entry.service_id,
        stylist_id=entry.stylist_id,
        start_ts=start_ts,
        end_ts=end_ts,
        status="confirmed",
        notes="Claimed from waitlist offer",
    )
    db.add(booking)
    entry.status = "claimed"
    await db.flush()

    # Create confirmation notification & email
    srv_name = entry.service.name if entry.service else "Service"
    st_name = entry.stylist.name if entry.stylist else "Stylist"
    subject, body = build_booking_confirmation_content(
        customer_name=user.name,
        service_name=srv_name,
        stylist_name=st_name,
        start_ts_str=start_ts.strftime("%Y-%m-%d %H:%M"),
        end_ts_str=end_ts.strftime("%H:%M"),
    )

    await create_notification(
        db=db,
        user_id=user.id,
        type="booking_confirmed",
        message=body,
        booking_id=booking.id,
        to_email=user.email,
        email_subject=subject,
        background_tasks=background_tasks,
    )

    await db.commit()
    await db.refresh(booking)
    return booking


async def expire_and_cascade_offers(
    db: AsyncSession,
    background_tasks: BackgroundTasks | None = None,
) -> int:
    """
    Scheduled job finding all expired 'offered' waitlist entries and cascading
    the slot to the next matching customer.
    """
    now_utc = datetime.now(timezone.utc)

    stmt = select(Waitlist).where(
        Waitlist.status == "offered",
        Waitlist.offer_expires_at <= now_utc,
    )
    expired_entries = (await db.execute(stmt)).scalars().all()
    if not expired_entries:
        return 0

    count = 0
    for entry in expired_entries:
        entry.status = "expired"
        await db.commit()
        count += 1

        # Notify the user their offer has expired
        await create_notification(
            db=db,
            user_id=entry.user_id,
            type="waitlist_expired",
            message="Your 15-minute window to claim an offered salon slot has expired.",
        )

        # Cascade slot to the next candidate
        if entry.offered_slot_start and entry.stylist_id:
            await offer_vacated_slot(
                service_id=entry.service_id,
                stylist_id=entry.stylist_id,
                slot_start=entry.offered_slot_start,
                db=db,
                background_tasks=background_tasks,
            )

    return count

