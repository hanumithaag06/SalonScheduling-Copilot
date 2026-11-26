# Why: Unit tests for the pure Python natural language intent parser.
# Validates 15 distinct customer sentence variations, budget extraction,
# time preference parsing, fuzzy service matching, and missing field follow-ups.

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import pytest

from app.engine.intent_parser import (
    parse_booking_intent,
    extract_budget,
    extract_time_preference,
    extract_service,
    extract_date,
)

# Reference timestamp for deterministic date parsing (Monday Nov 30, 2026)
REF_NOW = datetime(2026, 11, 30, 9, 0, tzinfo=timezone.utc)


def test_15_sample_sentences():
    """
    Tests 15 distinct real-world customer prompts covering services, dates,
    times, budget constraints, and missing field detections.
    """
    test_cases = [
        # 1. Full request: service + relative date + time
        {
            "text": "I want a classic haircut tomorrow afternoon",
            "expected_service": "Classic Haircut",
            "expected_time": "afternoon",
            "has_date": True,
            "missing": [],
        },
        # 2. Service + relative weekday + budget
        {
            "text": "Can I book balayage highlights next Monday under $160?",
            "expected_service": "Balayage Highlights",
            "expected_max_price": Decimal("160"),
            "has_date": True,
            "missing": [],
        },
        # 3. Service alias + ISO date + evening time
        {
            "text": "Need a beard trim on 2026-12-15 evening",
            "expected_service": "Beard Grooming & Shape",
            "expected_date": date(2026, 12, 15),
            "expected_time": "evening",
            "missing": [],
        },
        # 4. Service only (missing date)
        {
            "text": "Book me a haircut please",
            "expected_service": "Classic Haircut",
            "missing": ["date"],
        },
        # 5. Date and specific time only (missing service)
        {
            "text": "Something tomorrow at 2pm",
            "expected_time": "14:00",
            "has_date": True,
            "missing": ["service"],
        },
        # 6. Service + ISO date + word budget
        {
            "text": "Full hair color on 2026-12-20 budget 100",
            "expected_service": "Full Hair Color",
            "expected_date": date(2026, 12, 20),
            "expected_max_price": Decimal("100"),
            "missing": [],
        },
        # 7. Service + relative date + morning + max price
        {
            "text": "Deluxe cut and styling next Tuesday morning max 80",
            "expected_service": "Deluxe Cut & Styling",
            "expected_time": "morning",
            "expected_max_price": Decimal("80"),
            "has_date": True,
            "missing": [],
        },
        # 8. Signature Manicure + tomorrow
        {
            "text": "Signature manicure tomorrow",
            "expected_service": "Signature Manicure",
            "has_date": True,
            "missing": [],
        },
        # 9. Scalp massage alias + ISO date
        {
            "text": "Scalp massage on 2026-12-18",
            "expected_service": "Scalp Detox & Massage",
            "expected_date": date(2026, 12, 18),
            "missing": [],
        },
        # 10. Pedicure alias + afternoon + under budget
        {
            "text": "Express spa pedicure this Saturday afternoon under 50",
            "expected_service": "Express Spa Pedicure",
            "expected_time": "afternoon",
            "expected_max_price": Decimal("50"),
            "has_date": True,
            "missing": [],
        },
        # 11. Keratin treatment alias + relative date
        {
            "text": "Keratin smoothing treatment next Wednesday",
            "expected_service": "Keratin Smoothing Treatment",
            "has_date": True,
            "missing": [],
        },
        # 12. Root touch up + ISO date + evening
        {
            "text": "Root touch up on 2026-12-12 evening",
            "expected_service": "Root Touch-Up",
            "expected_date": date(2026, 12, 12),
            "expected_time": "evening",
            "missing": [],
        },
        # 13. Beard shape + morning + budget
        {
            "text": "Beard grooming and shape tomorrow morning budget 40",
            "expected_service": "Beard Grooming & Shape",
            "expected_time": "morning",
            "expected_max_price": Decimal("40"),
            "has_date": True,
            "missing": [],
        },
        # 14. Classic Cut + price + ISO date
        {
            "text": "Classic haircut under $30 on 2026-12-14",
            "expected_service": "Classic Haircut",
            "expected_date": date(2026, 12, 14),
            "expected_max_price": Decimal("30"),
            "missing": [],
        },
        # 15. Ambiguous date only (missing service)
        {
            "text": "I would like to make an appointment for next Friday",
            "has_date": True,
            "missing": ["service"],
        },
    ]

    assert len(test_cases) == 15

    for i, tc in enumerate(test_cases, start=1):
        parsed = parse_booking_intent(tc["text"], reference_now=REF_NOW)

        if "expected_service" in tc:
            assert parsed.service_name == tc["expected_service"], f"Case #{i} service failed for: {tc['text']}"

        if "expected_date" in tc:
            assert parsed.date == tc["expected_date"], f"Case #{i} date failed for: {tc['text']}"
        elif tc.get("has_date"):
            assert parsed.date is not None, f"Case #{i} should have parsed a date for: {tc['text']}"

        if "expected_time" in tc:
            assert parsed.time_pref == tc["expected_time"], f"Case #{i} time failed for: {tc['text']}"

        if "expected_max_price" in tc:
            assert parsed.max_price == tc["expected_max_price"], f"Case #{i} price failed for: {tc['text']}"

        assert parsed.missing_fields == tc["missing"], f"Case #{i} missing fields mismatch for: {tc['text']}"

        if tc["missing"]:
            assert parsed.follow_up_question is not None, f"Case #{i} must generate follow-up question"


def test_budget_extraction_patterns():
    """Validates regex price extractor across different phrasing."""
    assert extract_budget("budget under $45.00") == Decimal("45.00")
    assert extract_budget("max 80 dollars") == Decimal("80")
    assert extract_budget("less than 120 bucks") == Decimal("120")
    assert extract_budget("no price mentioned") is None


def test_time_preference_extraction():
    """Extracts morning, afternoon, evening, and clock times."""
    assert extract_time_preference("early morning appointment") == "morning"
    assert extract_time_preference("sometime in the afternoon") == "afternoon"
    assert extract_time_preference("late evening visit") == "evening"
    assert extract_time_preference("at 10:30 am") == "10:30"
    assert extract_time_preference("at 3:00 pm") == "15:00"
    assert extract_time_preference("at 14:00") == "14:00"


def test_missing_field_follow_up_questions():
    """Ensures clarifying follow-up questions are polite and informative."""
    p1 = parse_booking_intent("hello there", reference_now=REF_NOW)
    assert "service" in p1.missing_fields
    assert "date" in p1.missing_fields
    assert "What service would you like to book" in p1.follow_up_question

    p2 = parse_booking_intent("haircut", reference_now=REF_NOW)
    assert "date" in p2.missing_fields
    assert "What date would you like to schedule" in p2.follow_up_question

    p3 = parse_booking_intent("tomorrow", reference_now=REF_NOW)
    assert "service" in p3.missing_fields
    assert "Which salon service would you like to book" in p3.follow_up_question


def test_haircut_tomorrow_and_catalog_without_aliases():
    """Validates user prompt 'i would like to book for haircut tomorrow' with bare database catalog."""
    bare_catalog = [
        {"id": 1, "name": "Classic Haircut"},
        {"id": 2, "name": "Deluxe Cut & Styling"},
        {"id": 3, "name": "Beard Grooming & Shape"},
    ]
    parsed = parse_booking_intent(
        "i would like to book for haircut tomorrow",
        catalog=bare_catalog,
        reference_now=REF_NOW,
    )
    assert parsed.service_name == "Classic Haircut"
    assert parsed.service_id == 1
    assert parsed.date == date(2026, 12, 1)  # REF_NOW is Nov 30, so tomorrow is Dec 1
    assert parsed.missing_fields == []
    assert parsed.follow_up_question is None
