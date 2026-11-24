# Why: Pure computational waitlist matching and offer evaluation engine.
# Contains zero HTTP, DB, or framework dependencies so it can be tested in isolation.
# Determines candidate eligibility based on service, stylist, date, and time preference,
# enforcing strict First-Come, First-Served (FIFO) ordering and 15-minute offer windows.

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Sequence


@dataclass(frozen=True)
class WaitlistCandidate:
    """Represents a waiting customer request eligible for appointment slot offers."""
    id: int
    user_id: int
    service_id: int
    stylist_id: int | None
    date: date
    time_pref: str  # 'morning' | 'afternoon' | 'evening' | 'any'
    created_at: datetime

    def __post_init__(self):
        """Ensures creation timestamp is UTC-aware."""
        if self.created_at.tzinfo is None:
            object.__setattr__(self, "created_at", self.created_at.replace(tzinfo=timezone.utc))


def matches_time_preference(slot_time: time, time_pref: str) -> bool:
    """
    Checks if a slot start time matches a customer's time of day preference.
    Windows:
    - morning: 00:00 to 11:59:59 (< 12:00)
    - afternoon: 12:00 to 16:59:59 (12:00 <= t < 17:00)
    - evening: 17:00 onwards (>= 17:00)
    - any: matches all times
    """
    pref = time_pref.strip().lower()
    if pref in ("any", "*", "all"):
        return True
    elif pref in ("morning", "am"):
        return slot_time < time(12, 0)
    elif pref in ("afternoon", "pm"):
        return time(12, 0) <= slot_time < time(17, 0)
    elif pref in ("evening", "night"):
        return slot_time >= time(17, 0)
    return False


def is_candidate_eligible(
    candidate: WaitlistCandidate,
    slot_start: datetime,
    slot_stylist_id: int,
    service_id: int,
) -> bool:
    """
    Evaluates whether a candidate's request matches a freed appointment slot.
    Checks service ID, target date, stylist preference (or any), and time window.
    """
    # 1. Service match
    if candidate.service_id != service_id:
        return False

    # 2. Date match
    if candidate.date != slot_start.date():
        return False

    # 3. Stylist match (None means customer accepts any stylist)
    if candidate.stylist_id is not None and candidate.stylist_id != slot_stylist_id:
        return False

    # 4. Time of day preference match
    if not matches_time_preference(slot_start.time(), candidate.time_pref):
        return False

    return True


def select_next_waitlist_candidate(
    candidates: Sequence[WaitlistCandidate],
    slot_start: datetime,
    slot_stylist_id: int,
    service_id: int,
) -> WaitlistCandidate | None:
    """
    Pure selector returning the earliest eligible candidate (FIFO) for a vacated slot.
    Returns None if no candidate matches the criteria.
    """
    eligible = [
        c for c in candidates
        if is_candidate_eligible(c, slot_start, slot_stylist_id, service_id)
    ]
    if not eligible:
        return None

    # Earliest created entry wins (First-Come, First-Served)
    eligible.sort(key=lambda c: (c.created_at, c.id))
    return eligible[0]


def compute_offer_expiration(now_utc: datetime, window_minutes: int = 15) -> datetime:
    """Calculates the cutoff timestamp for a 15-minute waitlist slot claim window."""
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    return now_utc + timedelta(minutes=window_minutes)


def is_offer_expired(offer_expires_at: datetime | None, now_utc: datetime) -> bool:
    """Returns True if the offer claim deadline has passed."""
    if offer_expires_at is None:
        return True
    if offer_expires_at.tzinfo is None:
        offer_expires_at = offer_expires_at.replace(tzinfo=timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    return now_utc >= offer_expires_at

