# Why: Pydantic schemas for admin dashboard analytics and management responses.
# Models metric tiles: booking counts, revenue breakdown, utilization, heatmaps, and CSV/proxy operations.

from datetime import date as date_type, datetime, timezone
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_serializer


# ── Building-block row types ──────────────────────────────────────────────────

class BookingsPerDay(BaseModel):
    day: date_type
    count: int


class RevenuePerService(BaseModel):
    service_id: int
    service_name: str
    total_revenue: Decimal
    booking_count: int


class StylistUtilization(BaseModel):
    stylist_id: int
    stylist_name: str
    confirmed_bookings: int
    total_minutes_booked: int
    utilization_pct: float = Field(
        ...,
        description="Booked minutes / available shift minutes in the queried window, as a percentage",
    )


class PeakHour(BaseModel):
    hour: int = Field(..., description="Hour of day 0-23 (UTC)")
    booking_count: int


class HeatmapCell(BaseModel):
    weekday: int = Field(..., description="Day of week 0=Monday … 6=Sunday")
    hour: int = Field(..., description="Hour of day 0-23 (UTC)")
    booking_count: int


# ── Top-level dashboard payload ───────────────────────────────────────────────

class DashboardOut(BaseModel):
    period_from: date_type
    period_to: date_type
    total_bookings: int
    confirmed_bookings: int
    cancelled_bookings: int
    completed_bookings: int
    cancellation_rate_pct: float = Field(
        ...,
        description="Cancelled / total bookings as a percentage",
    )
    total_revenue: Decimal = Field(
        ...,
        description="Sum of service prices for confirmed + completed bookings",
    )
    bookings_per_day: list[BookingsPerDay]
    revenue_per_service: list[RevenuePerService]
    stylist_utilization: list[StylistUtilization]
    peak_hours: list[PeakHour] = Field(
        ...,
        description="Top 5 busiest hours of the day across the period",
    )
    heatmap: list[HeatmapCell] = Field(
        ...,
        description="Booking counts by (weekday, hour) for the full period",
    )


# ── Admin booking list (rich view for calendar & management) ─────────────────

class AdminBookingOut(BaseModel):
    id: int
    user_id: int
    user_name: str
    user_email: str
    service_id: int
    service_name: str
    stylist_id: int
    stylist_name: str
    start_ts: datetime
    end_ts: datetime
    status: str
    notes: str | None
    price: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("start_ts", "end_ts", "created_at", when_used="json")
    def serialize_utc_dt(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


# ── Admin proxy create (book on behalf of a customer) ────────────────────────

class AdminBookingCreate(BaseModel):
    user_id: int = Field(..., description="ID of the customer to book for")
    service_id: int = Field(..., description="ID of the salon service")
    stylist_id: int = Field(..., description="ID of the assigned stylist")
    start_ts: datetime = Field(..., description="Appointment start timestamp in UTC")
    notes: str | None = Field(default=None, max_length=500, description="Optional notes")
