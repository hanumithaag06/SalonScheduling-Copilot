# Why: Unit tests for the pure Python recommender engine (engine/recommender.py).
# Validates scoring components (loyalty, time preference, specialization, gap adjacency),
# explanation text generation, tie-breaking, top-3 filtering, and input-driven ranking changes.

from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
import pytest

from app.engine.recommender import (
    CandidateSlot,
    ExistingBooking,
    ScoreBreakdown,
    check_specialization_match,
    matches_preferred_time,
    is_adjacent_booking,
    recommend_slots,
)


def _dt(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def test_empty_candidates_returns_empty():
    """An empty candidate list produces an empty recommendation result."""
    result = recommend_slots(
        candidate_slots=[],
        service_name="Haircut",
        service_category="Hair",
    )
    assert result == []


def test_loyalty_scoring_scales_and_caps():
    """Past bookings award +1 per past visit, capped strictly at +3."""
    slot_1 = CandidateSlot(
        stylist_id=1,
        stylist_name="Alice",
        stylist_specialization="Haircuts",
        start_ts=_dt(2026, 12, 1, 10, 0),
        end_ts=_dt(2026, 12, 1, 10, 30),
        price=Decimal("40.00"),
    )
    slot_2 = CandidateSlot(
        stylist_id=2,
        stylist_name="Bob",
        stylist_specialization="Haircuts",
        start_ts=_dt(2026, 12, 1, 10, 0),
        end_ts=_dt(2026, 12, 1, 10, 30),
        price=Decimal("40.00"),
    )

    # 1 booking -> +1.0
    res_1 = recommend_slots([slot_1], "Haircut", "Hair", past_booking_counts={1: 1})
    assert res_1[0].score_breakdown.past_bookings == 1.0
    assert "1 time before" in res_1[0].reason

    # 2 bookings -> +2.0
    res_2 = recommend_slots([slot_1], "Haircut", "Hair", past_booking_counts={1: 2})
    assert res_2[0].score_breakdown.past_bookings == 2.0
    assert "2 times before" in res_2[0].reason

    # 5 bookings -> capped at +3.0
    res_3 = recommend_slots([slot_1], "Haircut", "Hair", past_booking_counts={1: 5})
    assert res_3[0].score_breakdown.past_bookings == 3.0
    assert "5 times before" in res_3[0].reason


def test_preferred_time_matching_and_scoring():
    """Candidate slots in the preferred time window earn +2."""
    morning_slot = CandidateSlot(
        stylist_id=1,
        stylist_name="Alice",
        stylist_specialization="Styling",
        start_ts=_dt(2026, 12, 1, 9, 30),
        end_ts=_dt(2026, 12, 1, 10, 0),
        price=Decimal("50.00"),
    )
    afternoon_slot = CandidateSlot(
        stylist_id=1,
        stylist_name="Alice",
        stylist_specialization="Styling",
        start_ts=_dt(2026, 12, 1, 14, 0),
        end_ts=_dt(2026, 12, 1, 14, 30),
        price=Decimal("50.00"),
    )
    evening_slot = CandidateSlot(
        stylist_id=1,
        stylist_name="Alice",
        stylist_specialization="Styling",
        start_ts=_dt(2026, 12, 1, 17, 30),
        end_ts=_dt(2026, 12, 1, 18, 0),
        price=Decimal("50.00"),
    )

    # Morning preference
    recs_morning = recommend_slots([morning_slot, afternoon_slot], "Blowout", "Styling", preferred_time="morning")
    assert recs_morning[0].start_ts == morning_slot.start_ts
    assert recs_morning[0].score_breakdown.preferred_time == 2.0

    # Afternoon preference
    recs_afternoon = recommend_slots([morning_slot, afternoon_slot], "Blowout", "Styling", preferred_time="afternoon")
    assert recs_afternoon[0].start_ts == afternoon_slot.start_ts
    assert recs_afternoon[0].score_breakdown.preferred_time == 2.0

    # Evening preference
    recs_evening = recommend_slots([morning_slot, evening_slot], "Blowout", "Styling", preferred_time="evening")
    assert recs_evening[0].start_ts == evening_slot.start_ts
    assert recs_evening[0].score_breakdown.preferred_time == 2.0

    # Explicit HH:MM preference (e.g. 14:15 matches 14:00 within 60 mins)
    recs_hhmm = recommend_slots([morning_slot, afternoon_slot], "Blowout", "Styling", preferred_time="14:15")
    assert recs_hhmm[0].start_ts == afternoon_slot.start_ts
    assert recs_hhmm[0].score_breakdown.preferred_time == 2.0


def test_specialization_matching():
    """Stylists with matching specialization earn +1 bonus."""
    color_stylist_slot = CandidateSlot(
        stylist_id=1,
        stylist_name="Alice",
        stylist_specialization="Coloring, Balayage, Highlights",
        start_ts=_dt(2026, 12, 1, 10, 0),
        end_ts=_dt(2026, 12, 1, 11, 0),
        price=Decimal("120.00"),
    )
    cut_stylist_slot = CandidateSlot(
        stylist_id=2,
        stylist_name="Bob",
        stylist_specialization="Men's Fade, Beard Grooming",
        start_ts=_dt(2026, 12, 1, 10, 0),
        end_ts=_dt(2026, 12, 1, 11, 0),
        price=Decimal("120.00"),
    )

    # Searching for Balayage service
    recs = recommend_slots(
        [cut_stylist_slot, color_stylist_slot],
        service_name="Balayage Highlights",
        service_category="Color",
    )
    # Alice should rank first due to specialization match
    assert recs[0].stylist_id == 1
    assert recs[0].score_breakdown.specialization == 1.0
    assert "specializes in" in recs[0].reason
    assert recs[1].score_breakdown.specialization == 0.0


def test_adjacent_booking_gap_filling_bonus():
    """Slots immediately before or after existing bookings earn +1 adjacency bonus."""
    # Existing booking: 11:00 - 12:00
    existing = [
        ExistingBooking(
            stylist_id=1,
            start_ts=_dt(2026, 12, 1, 11, 0),
            end_ts=_dt(2026, 12, 1, 12, 0),
        )
    ]

    # Slot adjacent before: 10:00 - 11:00 (ends exactly when existing booking starts)
    adjacent_before = CandidateSlot(
        stylist_id=1,
        stylist_name="Alice",
        stylist_specialization="General",
        start_ts=_dt(2026, 12, 1, 10, 0),
        end_ts=_dt(2026, 12, 1, 11, 0),
        price=Decimal("50.00"),
    )

    # Slot adjacent after: 12:00 - 13:00 (starts exactly when existing booking ends)
    adjacent_after = CandidateSlot(
        stylist_id=1,
        stylist_name="Alice",
        stylist_specialization="General",
        start_ts=_dt(2026, 12, 1, 12, 0),
        end_ts=_dt(2026, 12, 1, 13, 0),
        price=Decimal("50.00"),
    )

    # Isolated slot: 15:00 - 16:00
    isolated = CandidateSlot(
        stylist_id=1,
        stylist_name="Alice",
        stylist_specialization="General",
        start_ts=_dt(2026, 12, 1, 15, 0),
        end_ts=_dt(2026, 12, 1, 16, 0),
        price=Decimal("50.00"),
    )

    recs = recommend_slots(
        [isolated, adjacent_before, adjacent_after],
        service_name="Trim",
        service_category="Hair",
        existing_bookings=existing,
    )

    # Adjacent slots should score +1, while isolated scores 0
    adj_recs = [r for r in recs if r.score_breakdown.adjacent_booking == 1.0]
    assert len(adj_recs) == 2
    assert "Connects with an existing appointment" in adj_recs[0].reason

    isolated_rec = [r for r in recs if r.score_breakdown.adjacent_booking == 0.0][0]
    assert isolated_rec.score == 0.0


def test_ranking_changes_dynamically_with_inputs():
    """
    Demonstrates that changing input preferences (loyalty vs time vs specialization)
    actively alters the ranked order of the recommendations.
    """
    # Stylist 1: Alice (specialist in Color, afternoon slot)
    alice_slot = CandidateSlot(
        stylist_id=1,
        stylist_name="Alice",
        stylist_specialization="Hair Color Specialist",
        start_ts=_dt(2026, 12, 1, 14, 0),
        end_ts=_dt(2026, 12, 1, 15, 0),
        price=Decimal("100.00"),
    )

    # Stylist 2: Bob (specialist in Barbering, morning slot)
    bob_slot = CandidateSlot(
        stylist_id=2,
        stylist_name="Bob",
        stylist_specialization="Classic Barber Cuts",
        start_ts=_dt(2026, 12, 1, 10, 0),
        end_ts=_dt(2026, 12, 1, 11, 0),
        price=Decimal("100.00"),
    )

    candidates = [alice_slot, bob_slot]

    # Scenario A: Service is "Hair Color". No time preference, no loyalty.
    # Alice gets +1 (spec), Bob gets 0. Alice ranks #1.
    res_a = recommend_slots(candidates, "Hair Color", "Color")
    assert res_a[0].stylist_id == 1

    # Scenario B: Service is "Hair Color", BUT user prefers "morning" (+2).
    # Bob gets +2 (morning). Alice gets +1 (spec).
    # Bob should now beat Alice (2.0 > 1.0)!
    res_b = recommend_slots(candidates, "Hair Color", "Color", preferred_time="morning")
    assert res_b[0].stylist_id == 2
    assert res_b[0].score == 2.0
    assert res_b[1].stylist_id == 1
    assert res_b[1].score == 1.0

    # Scenario C: User prefers morning, BUT user has booked with Alice 3 times before (+3)!
    # Alice now gets: +1 (spec) + 3 (loyalty) = 4.0 points.
    # Bob gets: +2 (morning) = 2.0 points.
    # Alice takes back #1!
    res_c = recommend_slots(
        candidates,
        "Hair Color",
        "Color",
        preferred_time="morning",
        past_booking_counts={1: 3},
    )
    assert res_c[0].stylist_id == 1
    assert res_c[0].score == 4.0
    assert res_c[1].stylist_id == 2
    assert res_c[1].score == 2.0


def test_top_3_capped_and_deterministic_order():
    """Recommender returns at most top_n (default 3) items in deterministic order."""
    slots = [
        CandidateSlot(
            stylist_id=i,
            stylist_name=f"Stylist {i}",
            stylist_specialization="General",
            start_ts=_dt(2026, 12, 1, 9 + i, 0),
            end_ts=_dt(2026, 12, 1, 9 + i, 30),
            price=Decimal("40.00"),
        )
        for i in range(1, 6)
    ]

    recs = recommend_slots(slots, "Haircut", "Hair", top_n=3)
    assert len(recs) == 3
    # With equal scores (0), earlier slots sort first
    assert recs[0].start_ts < recs[1].start_ts < recs[2].start_ts

