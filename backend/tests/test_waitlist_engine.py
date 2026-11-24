# Why: Unit tests for the pure Python waitlist engine (engine/waitlist_engine.py).
# Validates FIFO candidate selection, eligibility rules, time preference matching,
# and offer expiration logic — all without any database or HTTP dependencies.

from datetime import date, datetime, time, timedelta, timezone
import pytest

from app.engine.waitlist_engine import (
    WaitlistCandidate,
    matches_time_preference,
    is_candidate_eligible,
    select_next_waitlist_candidate,
    compute_offer_expiration,
    is_offer_expired,
)


def _utc(year, month, day, hour=10, minute=0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def test_matches_time_preference_morning():
    """Morning preference matches slots before 12:00."""
    assert matches_time_preference(time(9, 30), "morning") is True
    assert matches_time_preference(time(11, 59), "morning") is True
    assert matches_time_preference(time(12, 0), "morning") is False


def test_matches_time_preference_afternoon():
    """Afternoon preference matches slots 12:00-16:59."""
    assert matches_time_preference(time(12, 0), "afternoon") is True
    assert matches_time_preference(time(16, 45), "afternoon") is True
    assert matches_time_preference(time(17, 0), "afternoon") is False


def test_matches_time_preference_evening():
    """Evening preference matches slots 17:00+."""
    assert matches_time_preference(time(17, 0), "evening") is True
    assert matches_time_preference(time(16, 59), "evening") is False


def test_matches_time_preference_any():
    """'any' preference matches all times."""
    for t in [time(0, 0), time(9, 30), time(13, 0), time(23, 59)]:
        assert matches_time_preference(t, "any") is True


def _make_candidate(id: int, service_id: int, stylist_id: int | None, target_date: date, time_pref: str, created_offset_sec: int = 0) -> WaitlistCandidate:
    return WaitlistCandidate(
        id=id,
        user_id=100 + id,
        service_id=service_id,
        stylist_id=stylist_id,
        date=target_date,
        time_pref=time_pref,
        created_at=_utc(2026, 12, 1, 8, 0) + timedelta(seconds=created_offset_sec),
    )


def test_is_candidate_eligible_service_mismatch():
    """Candidate requesting different service is not eligible."""
    slot_start = _utc(2026, 12, 1, 10, 0)
    cand = _make_candidate(1, service_id=99, stylist_id=1, target_date=date(2026, 12, 1), time_pref="any")
    assert is_candidate_eligible(cand, slot_start, slot_stylist_id=1, service_id=1) is False


def test_is_candidate_eligible_date_mismatch():
    """Candidate registered for a different date is not eligible."""
    slot_start = _utc(2026, 12, 2, 10, 0)  # Dec 2
    cand = _make_candidate(1, service_id=1, stylist_id=1, target_date=date(2026, 12, 1), time_pref="any")  # Dec 1
    assert is_candidate_eligible(cand, slot_start, slot_stylist_id=1, service_id=1) is False


def test_is_candidate_eligible_stylist_mismatch():
    """Candidate who requested a specific stylist cannot take another stylist's slot."""
    slot_start = _utc(2026, 12, 1, 10, 0)
    cand = _make_candidate(1, service_id=1, stylist_id=5, target_date=date(2026, 12, 1), time_pref="any")
    assert is_candidate_eligible(cand, slot_start, slot_stylist_id=3, service_id=1) is False


def test_is_candidate_eligible_stylist_none_accepts_any():
    """Candidate with no stylist preference accepts any stylist's freed slot."""
    slot_start = _utc(2026, 12, 1, 10, 0)
    cand = _make_candidate(1, service_id=1, stylist_id=None, target_date=date(2026, 12, 1), time_pref="any")
    assert is_candidate_eligible(cand, slot_start, slot_stylist_id=3, service_id=1) is True


def test_is_candidate_eligible_time_pref_mismatch():
    """Candidate requesting morning slots is not offered an afternoon slot."""
    slot_start = _utc(2026, 12, 1, 15, 0)  # 15:00 = afternoon
    cand = _make_candidate(1, service_id=1, stylist_id=None, target_date=date(2026, 12, 1), time_pref="morning")
    assert is_candidate_eligible(cand, slot_start, slot_stylist_id=1, service_id=1) is False


def test_select_next_waitlist_candidate_fifo_ordering():
    """The earliest eligible candidate (by created_at) wins (FIFO)."""
    target_date = date(2026, 12, 1)
    slot_start = _utc(2026, 12, 1, 10, 0)

    # Candidate 2 joined earlier but candidate 1 joined second
    cand_first = _make_candidate(1, service_id=1, stylist_id=None, target_date=target_date, time_pref="any", created_offset_sec=0)
    cand_second = _make_candidate(2, service_id=1, stylist_id=None, target_date=target_date, time_pref="any", created_offset_sec=60)

    result = select_next_waitlist_candidate(
        candidates=[cand_second, cand_first],  # deliberately out of order
        slot_start=slot_start,
        slot_stylist_id=1,
        service_id=1,
    )
    assert result is not None
    assert result.id == 1  # First registered wins


def test_select_next_waitlist_candidate_no_match():
    """Returns None when no candidate matches the freed slot."""
    target_date = date(2026, 12, 1)
    slot_start = _utc(2026, 12, 1, 10, 0)
    cand = _make_candidate(1, service_id=99, stylist_id=None, target_date=target_date, time_pref="any")

    result = select_next_waitlist_candidate(
        candidates=[cand],
        slot_start=slot_start,
        slot_stylist_id=1,
        service_id=1,
    )
    assert result is None


def test_compute_offer_expiration_window():
    """Offer expiry is exactly 15 minutes from now."""
    now = _utc(2026, 12, 1, 10, 0)
    expiry = compute_offer_expiration(now, window_minutes=15)
    assert expiry == _utc(2026, 12, 1, 10, 15)


def test_is_offer_expired_true_and_false():
    """is_offer_expired returns True past deadline and False before it."""
    now = _utc(2026, 12, 1, 10, 20)
    past_expiry = _utc(2026, 12, 1, 10, 15)   # expired 5 min ago
    future_expiry = _utc(2026, 12, 1, 10, 30)  # expires in 10 min

    assert is_offer_expired(past_expiry, now) is True
    assert is_offer_expired(future_expiry, now) is False
    assert is_offer_expired(None, now) is True  # no offer at all = expired
