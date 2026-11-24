# Why: Pure unit tests for the slot generation engine.
# Validates all edge cases: empty day, fully booked day, time-off overlap,
# full-day holiday, service longer than any gap, and shift day boundary.

from datetime import date, datetime, time, timedelta, timezone
from app.engine.slot_engine import (
    find_available_slots,
    StylistInfo,
    WorkingShift,
    TimeInterval,
)

# Deterministic test parameters
TEST_DATE = date(2026, 6, 1)  # Monday (weekday 0)
CURRENT_TIME = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)  # Previous day, no lead-time cutoff
STYLIST_1 = StylistInfo(id=1, name="Elena")
SHIFT_9_TO_17 = [WorkingShift(stylist_id=1, weekday=0, start_time=time(9, 0), end_time=time(17, 0))]


def test_empty_day():
    """Empty day with no bookings or time-off generates all slots in 15-min increments."""
    # 30-minute service on 09:00 - 12:00 shift (3 hours)
    short_shift = [WorkingShift(stylist_id=1, weekday=0, start_time=time(9, 0), end_time=time(12, 0))]

    slots = find_available_slots(
        service_duration_min=30,
        query_date=TEST_DATE,
        eligible_stylists=[STYLIST_1],
        working_hours=short_shift,
        time_off=[],
        confirmed_bookings=[],
        active_holds=[],
        current_time=CURRENT_TIME,
        lead_time_min=0,
    )

    # From 09:00 to 11:30 in 15-min steps: 11 possible start times
    assert len(slots) == 11
    assert slots[0].start_ts == datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc)
    assert slots[0].end_ts == datetime(2026, 6, 1, 9, 30, tzinfo=timezone.utc)
    assert slots[-1].start_ts == datetime(2026, 6, 1, 11, 30, tzinfo=timezone.utc)
    assert slots[-1].end_ts == datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)


def test_fully_booked_day():
    """A day completely packed with confirmed bookings yields zero available slots."""
    bookings = [
        TimeInterval(
            start_ts=datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 6, 1, 13, 0, tzinfo=timezone.utc),
        ),
        TimeInterval(
            start_ts=datetime(2026, 6, 1, 13, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 6, 1, 17, 0, tzinfo=timezone.utc),
        ),
    ]

    slots = find_available_slots(
        service_duration_min=30,
        query_date=TEST_DATE,
        eligible_stylists=[STYLIST_1],
        working_hours=SHIFT_9_TO_17,
        time_off=[],
        confirmed_bookings=bookings,
        active_holds=[],
        current_time=CURRENT_TIME,
        lead_time_min=0,
    )

    assert slots == []


def test_time_off_overlap():
    """Mid-day time-off (e.g. 12:00 - 14:00) blocks overlapping slots but allows earlier/later slots."""
    time_off = [
        TimeInterval(
            start_ts=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 6, 1, 14, 0, tzinfo=timezone.utc),
        )
    ]

    slots = find_available_slots(
        service_duration_min=60,
        query_date=TEST_DATE,
        eligible_stylists=[STYLIST_1],
        working_hours=SHIFT_9_TO_17,
        time_off=time_off,
        confirmed_bookings=[],
        active_holds=[],
        current_time=CURRENT_TIME,
        lead_time_min=0,
    )

    # Verify no slot overlaps with 12:00 - 14:00
    to_interval = time_off[0]
    for s in slots:
        slot_int = TimeInterval(s.start_ts, s.end_ts)
        assert not slot_int.overlaps(to_interval)

    # Latest slot before time-off ends at or before 12:00
    morning_slots = [s for s in slots if s.start_ts < to_interval.start_ts]
    assert morning_slots[-1].end_ts <= datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)

    # Earliest slot after time-off starts at or after 14:00
    afternoon_slots = [s for s in slots if s.start_ts >= to_interval.end_ts]
    assert afternoon_slots[0].start_ts >= datetime(2026, 6, 1, 14, 0, tzinfo=timezone.utc)


def test_holiday():
    """Full-day holiday or vacation leaves no bookable slots."""
    holiday = [
        TimeInterval(
            start_ts=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 6, 1, 23, 59, 59, tzinfo=timezone.utc),
        )
    ]

    slots = find_available_slots(
        service_duration_min=30,
        query_date=TEST_DATE,
        eligible_stylists=[STYLIST_1],
        working_hours=SHIFT_9_TO_17,
        time_off=holiday,
        confirmed_bookings=[],
        active_holds=[],
        current_time=CURRENT_TIME,
    )

    assert slots == []


def test_service_longer_than_any_gap():
    """If service duration is 60 min, but available gaps between bookings are only 45 min and 30 min, return []."""
    # Shift: 09:00 - 12:00.
    # Booking 1: 09:45 - 10:30 (leaves 09:00-09:45 = 45 min gap)
    # Booking 2: 11:00 - 12:00 (leaves 10:30-11:00 = 30 min gap)
    short_shift = [WorkingShift(stylist_id=1, weekday=0, start_time=time(9, 0), end_time=time(12, 0))]
    bookings = [
        TimeInterval(
            start_ts=datetime(2026, 6, 1, 9, 45, tzinfo=timezone.utc),
            end_ts=datetime(2026, 6, 1, 10, 30, tzinfo=timezone.utc),
        ),
        TimeInterval(
            start_ts=datetime(2026, 6, 1, 11, 0, tzinfo=timezone.utc),
            end_ts=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
        ),
    ]

    slots = find_available_slots(
        service_duration_min=60,  # Needs 60 min, max gap is 45 min
        query_date=TEST_DATE,
        eligible_stylists=[STYLIST_1],
        working_hours=short_shift,
        time_off=[],
        confirmed_bookings=bookings,
        active_holds=[],
        current_time=CURRENT_TIME,
        lead_time_min=0,
    )

    assert slots == []


def test_day_boundary():
    """A slot cannot cross the shift end boundary. 45-min service on 09:00-17:00 cannot start at 16:30."""
    slots = find_available_slots(
        service_duration_min=45,
        query_date=TEST_DATE,
        eligible_stylists=[STYLIST_1],
        working_hours=SHIFT_9_TO_17,
        time_off=[],
        confirmed_bookings=[],
        active_holds=[],
        current_time=CURRENT_TIME,
        lead_time_min=0,
    )

    # Last slot must finish exactly at or before 17:00
    last_slot = slots[-1]
    assert last_slot.start_ts == datetime(2026, 6, 1, 16, 15, tzinfo=timezone.utc)
    assert last_slot.end_ts == datetime(2026, 6, 1, 17, 0, tzinfo=timezone.utc)


def test_lead_time_and_buffer():
    """Tests that lead time filters out imminent slots and buffer reserves turnaround time."""
    # Current time is 10:00 AM on the same day; lead time is 45 minutes
    same_day_current_time = datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)

    # Booking at 11:30 - 12:00 with 15-min turnaround buffer (blocks until 12:15)
    bookings = [
        TimeInterval(
            start_ts=datetime(2026, 6, 1, 11, 30, tzinfo=timezone.utc),
            end_ts=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
        )
    ]

    slots = find_available_slots(
        service_duration_min=30,
        query_date=TEST_DATE,
        eligible_stylists=[STYLIST_1],
        working_hours=SHIFT_9_TO_17,
        time_off=[],
        confirmed_bookings=bookings,
        active_holds=[],
        current_time=same_day_current_time,
        lead_time_min=45,  # Earliest slot >= 10:45
        buffer_min=15,     # Booking at 11:30-12:00 blocks until 12:15
    )

    # First slot must be at or after 10:45
    assert slots[0].start_ts >= datetime(2026, 6, 1, 10, 45, tzinfo=timezone.utc)

    # No slot starts between 11:30 and 12:15
    for s in slots:
        assert not (
            datetime(2026, 6, 1, 11, 30, tzinfo=timezone.utc) <= s.start_ts < datetime(2026, 6, 1, 12, 15, tzinfo=timezone.utc)
        )

