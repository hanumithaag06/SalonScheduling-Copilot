# Why: Unit tests for the pure Python analytics service (services/analytics_service.py).
# Tests dashboard metrics: bookings per day, revenue per service, cancellation rate,
# stylist utilization %, peak hours, and heatmap calculation without DB or HTTP.

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import pytest

from app.services.analytics_service import (
    BookingRecord,
    StylistShiftRecord,
    compute_bookings_per_day,
    compute_revenue_per_service,
    compute_stylist_utilization,
    compute_peak_hours,
    compute_heatmap,
    compute_dashboard_stats,
)


def _dt(year: int, month: int, day: int, hour: int = 10, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def test_empty_bookings_analytics():
    """Empty booking sequence produces clean zero metrics."""
    stats = compute_dashboard_stats(
        bookings=[],
        shifts=[],
        period_from=date(2026, 11, 1),
        period_to=date(2026, 11, 30),
    )
    assert stats["total_bookings"] == 0
    assert stats["confirmed_bookings"] == 0
    assert stats["cancelled_bookings"] == 0
    assert stats["completed_bookings"] == 0
    assert stats["cancellation_rate_pct"] == 0.0
    assert stats["total_revenue"] == Decimal("0.00")
    assert stats["bookings_per_day"] == []
    assert stats["revenue_per_service"] == []
    assert stats["stylist_utilization"] == []
    assert stats["peak_hours"] == []
    assert stats["heatmap"] == []


def test_bookings_per_day_and_cancellation_rate():
    """Correctly groups bookings by day and calculates cancellation rate."""
    b1 = BookingRecord(
        id=1, status="completed",
        start_ts=_dt(2026, 11, 10, 10), end_ts=_dt(2026, 11, 10, 11),
        service_id=1, service_name="Cut", service_price=Decimal("40.00"),
        stylist_id=1, stylist_name="Alice",
    )
    b2 = BookingRecord(
        id=2, status="cancelled",
        start_ts=_dt(2026, 11, 10, 14), end_ts=_dt(2026, 11, 10, 15),
        service_id=1, service_name="Cut", service_price=Decimal("40.00"),
        stylist_id=1, stylist_name="Alice",
    )
    b3 = BookingRecord(
        id=3, status="confirmed",
        start_ts=_dt(2026, 11, 11, 10), end_ts=_dt(2026, 11, 11, 11),
        service_id=2, service_name="Color", service_price=Decimal("100.00"),
        stylist_id=2, stylist_name="Bob",
    )

    stats = compute_dashboard_stats(
        bookings=[b1, b2, b3],
        shifts=[],
        period_from=date(2026, 11, 10),
        period_to=date(2026, 11, 11),
    )

    assert stats["total_bookings"] == 3
    assert stats["confirmed_bookings"] == 1
    assert stats["cancelled_bookings"] == 1
    assert stats["completed_bookings"] == 1
    # 1 cancelled out of 3 = 33.3%
    assert stats["cancellation_rate_pct"] == 33.3

    # Cancelled bookings do NOT count towards revenue (40 + 100 = 140.00)
    assert stats["total_revenue"] == Decimal("140.00")

    # Bookings per day: Nov 10 has 2, Nov 11 has 1
    bpd = stats["bookings_per_day"]
    assert len(bpd) == 2
    assert bpd[0]["day"] == date(2026, 11, 10)
    assert bpd[0]["count"] == 2
    assert bpd[1]["day"] == date(2026, 11, 11)
    assert bpd[1]["count"] == 1


def test_revenue_per_service():
    """Ranks services by earned revenue (descending), omitting cancelled bookings."""
    b1 = BookingRecord(
        id=1, status="completed",
        start_ts=_dt(2026, 11, 10, 10), end_ts=_dt(2026, 11, 10, 11),
        service_id=1, service_name="Cut", service_price=Decimal("40.00"),
        stylist_id=1, stylist_name="Alice",
    )
    b2 = BookingRecord(
        id=2, status="confirmed",
        start_ts=_dt(2026, 11, 10, 12), end_ts=_dt(2026, 11, 10, 13),
        service_id=2, service_name="Balayage", service_price=Decimal("150.00"),
        stylist_id=1, stylist_name="Alice",
    )
    b3 = BookingRecord(
        id=3, status="cancelled",
        start_ts=_dt(2026, 11, 10, 14), end_ts=_dt(2026, 11, 10, 15),
        service_id=2, service_name="Balayage", service_price=Decimal("150.00"),
        stylist_id=1, stylist_name="Alice",
    )

    rps = compute_revenue_per_service([b1, b2, b3])
    assert len(rps) == 2
    # Balayage ranked #1 ($150), Cut ranked #2 ($40)
    assert rps[0]["service_name"] == "Balayage"
    assert rps[0]["total_revenue"] == Decimal("150.00")
    assert rps[0]["booking_count"] == 1

    assert rps[1]["service_name"] == "Cut"
    assert rps[1]["total_revenue"] == Decimal("40.00")
    assert rps[1]["booking_count"] == 1


def test_stylist_utilization():
    """Computes utilization percentage = booked minutes / shift minutes * 100."""
    # Alice works Monday (weekday 0) from 09:00 to 17:00 = 8 hours = 480 minutes
    # Monday Nov 2, 2026
    shift = StylistShiftRecord(stylist_id=1, weekday=0, minutes=480)

    # 120 minutes booked on Monday Nov 2, 2026
    b1 = BookingRecord(
        id=1, status="confirmed",
        start_ts=_dt(2026, 11, 2, 10, 0), end_ts=_dt(2026, 11, 2, 12, 0),
        service_id=1, service_name="Cut", service_price=Decimal("60.00"),
        stylist_id=1, stylist_name="Alice",
    )

    util = compute_stylist_utilization(
        bookings=[b1],
        shifts=[shift],
        period_from=date(2026, 11, 2),
        period_to=date(2026, 11, 2),
    )
    assert len(util) == 1
    # 120 / 480 = 25.0%
    assert util[0]["stylist_name"] == "Alice"
    assert util[0]["total_minutes_booked"] == 120
    assert util[0]["utilization_pct"] == 25.0


def test_peak_hours_and_heatmap():
    """Peak hours identifies top volume hours, and heatmap indexes (weekday, hour)."""
    # 2 bookings at 10:00, 1 at 14:00 on Monday Nov 2
    b1 = BookingRecord(
        id=1, status="confirmed",
        start_ts=_dt(2026, 11, 2, 10, 0), end_ts=_dt(2026, 11, 2, 10, 30),
        service_id=1, service_name="Cut", service_price=Decimal("40.00"),
        stylist_id=1, stylist_name="Alice",
    )
    b2 = BookingRecord(
        id=2, status="confirmed",
        start_ts=_dt(2026, 11, 2, 10, 30), end_ts=_dt(2026, 11, 2, 11, 0),
        service_id=1, service_name="Cut", service_price=Decimal("40.00"),
        stylist_id=2, stylist_name="Bob",
    )
    b3 = BookingRecord(
        id=3, status="confirmed",
        start_ts=_dt(2026, 11, 2, 14, 0), end_ts=_dt(2026, 11, 2, 15, 0),
        service_id=1, service_name="Cut", service_price=Decimal("40.00"),
        stylist_id=1, stylist_name="Alice",
    )

    peak = compute_peak_hours([b1, b2, b3], top_n=2)
    assert len(peak) == 2
    assert peak[0]["hour"] == 10
    assert peak[0]["booking_count"] == 2
    assert peak[1]["hour"] == 14
    assert peak[1]["booking_count"] == 1

    heatmap = compute_heatmap([b1, b2, b3])
    # Monday is weekday 0
    assert len(heatmap) == 2
    assert heatmap[0]["weekday"] == 0
    assert heatmap[0]["hour"] == 10
    assert heatmap[0]["booking_count"] == 2
    assert heatmap[1]["weekday"] == 0
    assert heatmap[1]["hour"] == 14
    assert heatmap[1]["booking_count"] == 1
