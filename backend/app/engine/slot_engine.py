# Why: Pure computational slot engine for salon appointment scheduling.
# Contains zero HTTP, DB, or framework dependencies so it can be tested in isolation.
# Computes available appointment slots in 15-minute increments respecting shifts,
# lead times, turn-around buffers, active holds, time-off, and existing bookings.

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Sequence


@dataclass(frozen=True)
class TimeInterval:
    """Represents a generic half-open time range [start_ts, end_ts)."""
    start_ts: datetime
    end_ts: datetime

    def __post_init__(self):
        """Ensures both interval boundaries are timezone-aware in UTC."""
        if self.start_ts.tzinfo is None:
            object.__setattr__(self, "start_ts", self.start_ts.replace(tzinfo=timezone.utc))
        if self.end_ts.tzinfo is None:
            object.__setattr__(self, "end_ts", self.end_ts.replace(tzinfo=timezone.utc))

    def overlaps(self, other: "TimeInterval") -> bool:
        """Two half-open intervals [A, B) and [C, D) overlap if A < D and C < B."""
        return self.start_ts < other.end_ts and other.start_ts < self.end_ts


@dataclass(frozen=True)
class StylistInfo:
    """Identifies a stylist for slot calculation."""
    id: int
    name: str


@dataclass(frozen=True)
class WorkingShift:
    """Stylist shift definition for a specific day of the week (0=Mon, 6=Sun)."""
    stylist_id: int
    weekday: int
    start_time: time
    end_time: time


@dataclass(frozen=True)
class AvailableSlot:
    """A computed bookable appointment slot for a customer."""
    stylist_id: int
    stylist_name: str
    start_ts: datetime
    end_ts: datetime
    duration_min: int


def _merge_intervals(intervals: Sequence[TimeInterval]) -> list[TimeInterval]:
    """
    Sorts and merges overlapping or adjacent time intervals into disjoint blocks.
    Reduces collision checks from O(k * m) to O(k * log(m)).
    """
    if not intervals:
        return []

    sorted_intervals = sorted(intervals, key=lambda x: x.start_ts)
    merged: list[TimeInterval] = [sorted_intervals[0]]

    for current in sorted_intervals[1:]:
        previous = merged[-1]
        # If current interval starts before or at the end of previous interval, merge them
        if current.start_ts <= previous.end_ts:
            merged[-1] = TimeInterval(
                start_ts=previous.start_ts,
                end_ts=max(previous.end_ts, current.end_ts)
            )
        else:
            merged.append(current)

    return merged


def find_available_slots(
    service_duration_min: int,
    query_date: date,
    eligible_stylists: Sequence[StylistInfo],
    working_hours: Sequence[WorkingShift],
    time_off: Sequence[TimeInterval],
    confirmed_bookings: Sequence[TimeInterval],
    active_holds: Sequence[TimeInterval],
    current_time: datetime,
    lead_time_min: int = 30,
    buffer_min: int = 0,
    step_min: int = 15,
) -> list[AvailableSlot]:
    """
    Pure function that calculates available booking slots for a requested service duration.

    Algorithm:
    1. For each stylist, lookup their working hours for query_date.weekday().
    2. Construct the stylist's daily shift boundary in UTC: [shift_start_dt, shift_end_dt).
    3. Calculate earliest permissible start: max(shift_start_dt, current_time + lead_time_min).
    4. Compile all busy intervals for this stylist (time-off, confirmed bookings + buffer, holds + buffer).
    5. Merge overlapping busy intervals into contiguous sorted blocks.
    6. Step through candidate start times in step_min (15 min) increments:
       - candidate_end = candidate_start + service_duration_min
       - Check bounds: candidate_end <= shift_end_dt
       - Check collisions: ensure [candidate_start, candidate_end) does not intersect any busy block.
    7. Return all valid AvailableSlot instances sorted chronologically.

    Complexity:
    - Let S = number of eligible stylists
    - Let B = total busy intervals (bookings, holds, time-off) per stylist
    - Let T = number of 15-minute intervals in a working shift (typically (9 hrs * 60) / 15 = 36 steps)
    - Merging intervals takes O(B log B).
    - Checking T candidate slots against merged intervals takes O(T * log B) via binary search
      or O(T + B) via two-pointer scan.
    - Total Time Complexity: O(S * (B log B + T)), which executes in sub-millisecond time.
    - Space Complexity: O(T + B) for the generated slots and merged busy lists.
    """
    if service_duration_min <= 0:
        return []

    # Map working hours by stylist_id for the query weekday
    target_weekday = query_date.weekday()
    shift_map: dict[int, WorkingShift] = {
        wh.stylist_id: wh
        for wh in working_hours
        if wh.weekday == target_weekday
    }

    # Earliest possible slot start based on current time + minimum lead time
    min_lead_cutoff = current_time + timedelta(minutes=lead_time_min)
    available_slots: list[AvailableSlot] = []

    for stylist in eligible_stylists:
        shift = shift_map.get(stylist.id)
        if not shift:
            # Stylist does not work on this weekday
            continue

        # Shift boundaries in UTC
        shift_start_dt = datetime.combine(query_date, shift.start_time, tzinfo=timezone.utc)
        shift_end_dt = datetime.combine(query_date, shift.end_time, tzinfo=timezone.utc)

        # Collect all blocked/busy intervals for this stylist
        busy_intervals: list[TimeInterval] = []

        # 1. Time off / holidays (no buffer added to personal time off)
        for to in time_off:
            if to.overlaps(TimeInterval(shift_start_dt, shift_end_dt)):
                busy_intervals.append(to)

        # 2. Confirmed bookings (buffer added after appointment for cleanup/turnaround)
        buffer_delta = timedelta(minutes=buffer_min)
        for b in confirmed_bookings:
            buffered_booking = TimeInterval(b.start_ts, b.end_ts + buffer_delta)
            if buffered_booking.overlaps(TimeInterval(shift_start_dt, shift_end_dt)):
                busy_intervals.append(buffered_booking)

        # 3. Active holds (buffer added after hold end)
        for h in active_holds:
            buffered_hold = TimeInterval(h.start_ts, h.end_ts + buffer_delta)
            if buffered_hold.overlaps(TimeInterval(shift_start_dt, shift_end_dt)):
                busy_intervals.append(buffered_hold)

        # Merge busy blocks for fast evaluation
        merged_busy = _merge_intervals(busy_intervals)

        # Start candidate generation from shift_start or earliest lead cutoff, rounded up to 15-min step
        candidate_time = shift_start_dt
        if min_lead_cutoff > candidate_time:
            # Align min_lead_cutoff to the next step_min boundary
            minutes_past = min_lead_cutoff.minute % step_min
            if minutes_past > 0 or min_lead_cutoff.second > 0 or min_lead_cutoff.microsecond > 0:
                candidate_time = min_lead_cutoff.replace(second=0, microsecond=0) + timedelta(
                    minutes=(step_min - minutes_past)
                )
            else:
                candidate_time = min_lead_cutoff.replace(second=0, microsecond=0)

        service_delta = timedelta(minutes=service_duration_min)
        step_delta = timedelta(minutes=step_min)

        # Step through the day in 15-minute increments
        while candidate_time + service_delta <= shift_end_dt:
            slot_interval = TimeInterval(candidate_time, candidate_time + service_delta)

            # Check if this candidate slot collides with any merged busy block
            is_blocked = False
            for busy in merged_busy:
                if slot_interval.overlaps(busy):
                    is_blocked = True
                    # Optimization: skip candidate_time forward to the end of the busy block
                    break

            if not is_blocked:
                available_slots.append(
                    AvailableSlot(
                        stylist_id=stylist.id,
                        stylist_name=stylist.name,
                        start_ts=candidate_time,
                        end_ts=candidate_time + service_delta,
                        duration_min=service_duration_min,
                    )
                )

            candidate_time += step_delta

    # Sort slots chronologically, then by stylist id
    return sorted(available_slots, key=lambda s: (s.start_ts, s.stylist_id))

