# Why: Pure analytics computation service for the admin dashboard.
# All aggregation runs in Python after a single bulk query per metric,
# so it stays testable without HTTP or the full ORM relationship graph.

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Sequence


@dataclass(frozen=True)
class BookingRecord:
    """Lightweight snapshot of a booking row used for analytics computation."""
    id: int
    status: str            # 'confirmed' | 'cancelled' | 'completed'
    start_ts: datetime
    end_ts: datetime
    service_id: int
    service_name: str
    service_price: Decimal
    stylist_id: int
    stylist_name: str

    def __post_init__(self):
        """Normalises timestamps to UTC-aware."""
        if self.start_ts.tzinfo is None:
            object.__setattr__(self, "start_ts", self.start_ts.replace(tzinfo=timezone.utc))
        if self.end_ts.tzinfo is None:
            object.__setattr__(self, "end_ts", self.end_ts.replace(tzinfo=timezone.utc))


@dataclass(frozen=True)
class StylistShiftRecord:
    """Working-hours entry for stylist utilization calculation."""
    stylist_id: int
    weekday: int   # 0 = Monday … 6 = Sunday
    minutes: int   # shift length in minutes (end_time − start_time)


# ── Metric helpers ────────────────────────────────────────────────────────────

def compute_bookings_per_day(
    bookings: Sequence[BookingRecord],
) -> list[dict]:
    """Counts all bookings grouped by their UTC start date, sorted ascending."""
    counter: dict[date, int] = defaultdict(int)
    for b in bookings:
        counter[b.start_ts.date()] += 1
    return [{"day": d, "count": c} for d, c in sorted(counter.items())]


def compute_revenue_per_service(
    bookings: Sequence[BookingRecord],
) -> list[dict]:
    """
    Sums service prices for confirmed + completed bookings.
    Returns list of dicts with service_id, service_name, total_revenue, booking_count.
    """
    revenue: dict[int, Decimal] = defaultdict(Decimal)
    count: dict[int, int] = defaultdict(int)
    names: dict[int, str] = {}

    for b in bookings:
        if b.status in ("confirmed", "completed"):
            revenue[b.service_id] += b.service_price
            count[b.service_id] += 1
            names[b.service_id] = b.service_name

    rows = [
        {
            "service_id": sid,
            "service_name": names[sid],
            "total_revenue": revenue[sid],
            "booking_count": count[sid],
        }
        for sid in sorted(revenue.keys())
    ]
    # Sort by revenue descending
    rows.sort(key=lambda r: r["total_revenue"], reverse=True)
    return rows


def compute_stylist_utilization(
    bookings: Sequence[BookingRecord],
    shifts: Sequence[StylistShiftRecord],
    period_from: date,
    period_to: date,
) -> list[dict]:
    """
    Calculates utilization as booked_minutes / available_shift_minutes × 100.
    Available minutes = sum of daily shift minutes across days in [period_from, period_to]
    for each stylist's working weekdays.
    """
    num_days = (period_to - period_from).days + 1

    # Map: stylist_id → available minutes in the whole window
    shift_map: dict[int, int] = defaultdict(int)
    for s in shifts:
        # Count how many times this weekday occurs in the period
        occurrences = sum(
            1 for i in range(num_days)
            if (period_from + timedelta(days=i)).weekday() == s.weekday
        )
        shift_map[s.stylist_id] += s.minutes * occurrences

    # Confirmed + completed bookings grouped by stylist
    booked: dict[int, int] = defaultdict(int)
    confirmed: dict[int, int] = defaultdict(int)
    names: dict[int, str] = {}

    for b in bookings:
        if b.status in ("confirmed", "completed"):
            duration = int((b.end_ts - b.start_ts).total_seconds() // 60)
            booked[b.stylist_id] += duration
            confirmed[b.stylist_id] += 1
            names[b.stylist_id] = b.stylist_name

    all_stylist_ids = set(shift_map.keys()) | set(booked.keys())
    rows = []
    for sid in sorted(all_stylist_ids):
        avail = shift_map.get(sid, 0)
        bk_min = booked.get(sid, 0)
        pct = round((bk_min / avail * 100) if avail > 0 else 0.0, 1)
        rows.append({
            "stylist_id": sid,
            "stylist_name": names.get(sid, f"Stylist #{sid}"),
            "confirmed_bookings": confirmed.get(sid, 0),
            "total_minutes_booked": bk_min,
            "utilization_pct": pct,
        })

    rows.sort(key=lambda r: r["utilization_pct"], reverse=True)
    return rows


def compute_peak_hours(
    bookings: Sequence[BookingRecord],
    top_n: int = 5,
) -> list[dict]:
    """
    Returns the top N busiest hours-of-day (UTC, 0-23) sorted by booking count desc.
    """
    counter: dict[int, int] = defaultdict(int)
    for b in bookings:
        counter[b.start_ts.hour] += 1

    ranked = sorted(counter.items(), key=lambda x: x[1], reverse=True)
    return [{"hour": hr, "booking_count": cnt} for hr, cnt in ranked[:top_n]]


def compute_heatmap(
    bookings: Sequence[BookingRecord],
) -> list[dict]:
    """
    Builds a (weekday, hour, count) heatmap of booking volume.
    weekday: 0=Monday … 6=Sunday; hour: 0-23 UTC.
    """
    grid: dict[tuple[int, int], int] = defaultdict(int)
    for b in bookings:
        key = (b.start_ts.weekday(), b.start_ts.hour)
        grid[key] += 1

    rows = [
        {"weekday": wd, "hour": hr, "booking_count": cnt}
        for (wd, hr), cnt in sorted(grid.items(), key=lambda x: (x[0][0], x[0][1]))
    ]
    return rows


def compute_dashboard_stats(
    bookings: Sequence[BookingRecord],
    shifts: Sequence[StylistShiftRecord],
    period_from: date,
    period_to: date,
) -> dict:
    """
    Aggregates all dashboard metrics in one pass. Pure function — no I/O.
    Returns a dict matching DashboardOut field names.
    """
    total = len(bookings)
    confirmed = sum(1 for b in bookings if b.status == "confirmed")
    cancelled = sum(1 for b in bookings if b.status == "cancelled")
    completed = sum(1 for b in bookings if b.status == "completed")
    cancel_rate = round((cancelled / total * 100) if total else 0.0, 1)
    total_revenue = sum(
        (b.service_price for b in bookings if b.status in ("confirmed", "completed")),
        Decimal("0.00"),
    )

    return {
        "period_from": period_from,
        "period_to": period_to,
        "total_bookings": total,
        "confirmed_bookings": confirmed,
        "cancelled_bookings": cancelled,
        "completed_bookings": completed,
        "cancellation_rate_pct": cancel_rate,
        "total_revenue": total_revenue,
        "bookings_per_day": compute_bookings_per_day(bookings),
        "revenue_per_service": compute_revenue_per_service(bookings),
        "stylist_utilization": compute_stylist_utilization(bookings, shifts, period_from, period_to),
        "peak_hours": compute_peak_hours(bookings),
        "heatmap": compute_heatmap(bookings),
    }
