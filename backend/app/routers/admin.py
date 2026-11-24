# Why: Admin management router: dashboard analytics, calendar filtering,
# CSV export, and proxy create/cancel actions on behalf of customers.

import csv
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import io
import json
from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.core.errors import NotFoundException
from app.db.session import get_db
from app.models import Booking, Service, Stylist, User, WorkingHours, AuditLog
from app.schemas.admin import (
    DashboardOut,
    AdminBookingOut,
    AdminBookingCreate,
)
from app.schemas.booking import BookingCreate, BookingOut
from app.services.analytics_service import (
    BookingRecord,
    StylistShiftRecord,
    compute_dashboard_stats,
)
from app.services.booking_service import create_booking, cancel_booking

router = APIRouter(prefix="/admin", tags=["admin"])


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.get("/bookings", response_model=list[AdminBookingOut])
async def list_admin_bookings(
    from_date: date | None = Query(default=None, alias="from", description="Start date (YYYY-MM-DD)"),
    to_date: date | None = Query(default=None, alias="to", description="End date (YYYY-MM-DD)"),
    stylist_id: int | None = Query(default=None, description="Filter by stylist ID"),
    status: str | None = Query(default=None, description="Filter by booking status"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns filtered bookings across the salon for calendar and table views.
    Protected by admin role requirement.
    """
    stmt = (
        select(Booking)
        .options(
            selectinload(Booking.user),
            selectinload(Booking.service),
            selectinload(Booking.stylist),
        )
        .order_by(Booking.start_ts.asc())
        .limit(limit)
        .offset(offset)
    )

    if from_date:
        start_boundary = datetime.combine(from_date, time.min, tzinfo=timezone.utc)
        stmt = stmt.where(Booking.start_ts >= start_boundary)

    if to_date:
        end_boundary = datetime.combine(to_date, time.max, tzinfo=timezone.utc)
        stmt = stmt.where(Booking.start_ts <= end_boundary)

    if stylist_id:
        stmt = stmt.where(Booking.stylist_id == stylist_id)

    if status:
        stmt = stmt.where(Booking.status == status)

    bookings = (await db.execute(stmt)).scalars().all()

    results: list[AdminBookingOut] = []
    for b in bookings:
        results.append(
            AdminBookingOut(
                id=b.id,
                user_id=b.user_id,
                user_name=b.user.name if b.user else "Unknown User",
                user_email=b.user.email if b.user else "unknown@example.com",
                service_id=b.service_id,
                service_name=b.service.name if b.service else "Service",
                stylist_id=b.stylist_id,
                stylist_name=b.stylist.name if b.stylist else "Stylist",
                start_ts=_ensure_utc(b.start_ts),
                end_ts=_ensure_utc(b.end_ts),
                status=b.status,
                notes=b.notes,
                price=b.service.price if b.service else Decimal("0.00"),
                created_at=_ensure_utc(b.created_at),
            )
        )
    return results


@router.get("/dashboard", response_model=DashboardOut)
async def get_dashboard_analytics(
    from_date: date | None = Query(default=None, alias="from", description="Start date (YYYY-MM-DD)"),
    to_date: date | None = Query(default=None, alias="to", description="End date (YYYY-MM-DD)"),
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Aggregates salon business metrics: totals, cancellation rate, revenue per service,
    bookings per day, stylist utilization, peak hours, and heatmap.
    """
    today = datetime.now(timezone.utc).date()
    period_from = from_date or (today - timedelta(days=60))
    period_to = to_date or (today + timedelta(days=30))

    start_boundary = datetime.combine(period_from, time.min, tzinfo=timezone.utc)
    end_boundary = datetime.combine(period_to, time.max, tzinfo=timezone.utc)

    # 1. Fetch bookings in range
    bk_stmt = (
        select(Booking)
        .options(selectinload(Booking.service), selectinload(Booking.stylist))
        .where(Booking.start_ts >= start_boundary, Booking.start_ts <= end_boundary)
    )
    bookings = (await db.execute(bk_stmt)).scalars().all()

    # 2. Fetch all working hours shifts for utilization calculation
    wh_stmt = select(WorkingHours)
    wh_records = (await db.execute(wh_stmt)).scalars().all()

    booking_records = [
        BookingRecord(
            id=b.id,
            status=b.status,
            start_ts=_ensure_utc(b.start_ts),
            end_ts=_ensure_utc(b.end_ts),
            service_id=b.service_id,
            service_name=b.service.name if b.service else "Service",
            service_price=b.service.price if b.service else Decimal("0.00"),
            stylist_id=b.stylist_id,
            stylist_name=b.stylist.name if b.stylist else "Stylist",
        )
        for b in bookings
    ]

    shift_records = [
        StylistShiftRecord(
            stylist_id=wh.stylist_id,
            weekday=wh.weekday,
            minutes=int(
                (
                    datetime.combine(date.today(), wh.end_time)
                    - datetime.combine(date.today(), wh.start_time)
                ).total_seconds()
                // 60
            ),
        )
        for wh in wh_records
    ]

    stats = compute_dashboard_stats(
        bookings=booking_records,
        shifts=shift_records,
        period_from=period_from,
        period_to=period_to,
    )
    return DashboardOut(**stats)


@router.get("/export/bookings.csv")
async def export_bookings_csv(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    stylist_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Exports filtered bookings as a CSV file.
    """
    stmt = (
        select(Booking)
        .options(
            selectinload(Booking.user),
            selectinload(Booking.service),
            selectinload(Booking.stylist),
        )
        .order_by(Booking.start_ts.asc())
    )

    if from_date:
        stmt = stmt.where(Booking.start_ts >= datetime.combine(from_date, time.min, tzinfo=timezone.utc))
    if to_date:
        stmt = stmt.where(Booking.start_ts <= datetime.combine(to_date, time.max, tzinfo=timezone.utc))
    if stylist_id:
        stmt = stmt.where(Booking.stylist_id == stylist_id)
    if status:
        stmt = stmt.where(Booking.status == status)

    bookings = (await db.execute(stmt)).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "booking_id",
        "customer_id",
        "customer_name",
        "customer_email",
        "service_id",
        "service_name",
        "stylist_id",
        "stylist_name",
        "start_time_utc",
        "end_time_utc",
        "status",
        "price",
        "notes",
        "created_at_utc",
    ])

    for b in bookings:
        writer.writerow([
            b.id,
            b.user_id,
            b.user.name if b.user else "",
            b.user.email if b.user else "",
            b.service_id,
            b.service.name if b.service else "",
            b.stylist_id,
            b.stylist.name if b.stylist else "",
            _ensure_utc(b.start_ts).isoformat(),
            _ensure_utc(b.end_ts).isoformat(),
            b.status,
            str(b.service.price) if b.service else "0.00",
            b.notes or "",
            _ensure_utc(b.created_at).isoformat(),
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="bookings.csv"'},
    )


@router.post("/bookings", response_model=AdminBookingOut, status_code=status.HTTP_201_CREATED)
async def admin_create_booking_for_customer(
    payload: AdminBookingCreate,
    background_tasks: BackgroundTasks,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates an appointment on behalf of a customer.
    Logs an audit event noting the administrator who booked the slot.
    """
    u_stmt = select(User).where(User.id == payload.user_id)
    customer = (await db.execute(u_stmt)).scalar_one_or_none()
    if not customer:
        raise NotFoundException(detail="Customer user not found", code="USER_NOT_FOUND")

    booking_payload = BookingCreate(
        service_id=payload.service_id,
        stylist_id=payload.stylist_id,
        start_ts=payload.start_ts,
        notes=payload.notes,
    )

    booking = await create_booking(
        payload=booking_payload,
        user=customer,
        db=db,
        background_tasks=background_tasks,
    )

    # Log admin proxy audit action
    audit = AuditLog(
        actor_id=current_admin.id,
        action="ADMIN_CREATE",
        entity="booking",
        entity_id=booking.id,
        details=json.dumps({
            "proxy_for_user_id": customer.id,
            "service_id": payload.service_id,
            "stylist_id": payload.stylist_id,
        }),
    )
    db.add(audit)
    await db.commit()

    return AdminBookingOut(
        id=booking.id,
        user_id=customer.id,
        user_name=customer.name,
        user_email=customer.email,
        service_id=booking.service_id,
        service_name=booking.service.name if booking.service else "Service",
        stylist_id=booking.stylist_id,
        stylist_name=booking.stylist.name if booking.stylist else "Stylist",
        start_ts=_ensure_utc(booking.start_ts),
        end_ts=_ensure_utc(booking.end_ts),
        status=booking.status,
        notes=booking.notes,
        price=booking.service.price if booking.service else Decimal("0.00"),
        created_at=_ensure_utc(booking.created_at),
    )


@router.post("/bookings/{booking_id}/cancel", response_model=BookingOut)
async def admin_cancel_booking(
    booking_id: int,
    background_tasks: BackgroundTasks,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancels an appointment on behalf of a customer.
    Admin overrides user ownership and triggers waitlist cascading.
    """
    booking = await cancel_booking(
        booking_id=booking_id,
        user=current_admin,
        db=db,
        background_tasks=background_tasks,
    )

    audit = AuditLog(
        actor_id=current_admin.id,
        action="ADMIN_CANCEL",
        entity="booking",
        entity_id=booking.id,
        details=json.dumps({"cancelled_by_admin": current_admin.id}),
    )
    db.add(audit)
    await db.commit()

    return booking
