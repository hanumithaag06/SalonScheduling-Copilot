# Why: Pure computational rule-based recommender for salon appointment slots.
# Contains zero HTTP, DB, or framework dependencies so it can be tested in isolation.
# Scores (stylist, slot) candidate pairs using an explainable multi-factor heuristic:
# +3 loyalty bonus (scaled and capped), +2 time preference, +1 specialization match,
# +1 schedule adjacency (gap-filling). Returns the top 3 with clear human-readable reasons.

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
import re
from typing import Sequence


@dataclass(frozen=True)
class CandidateSlot:
    """Represents an available appointment slot evaluated by the recommender."""
    stylist_id: int
    stylist_name: str
    stylist_specialization: str
    start_ts: datetime
    end_ts: datetime
    price: Decimal

    def __post_init__(self):
        """Ensures both interval boundaries are timezone-aware in UTC."""
        if self.start_ts.tzinfo is None:
            object.__setattr__(self, "start_ts", self.start_ts.replace(tzinfo=timezone.utc))
        if self.end_ts.tzinfo is None:
            object.__setattr__(self, "end_ts", self.end_ts.replace(tzinfo=timezone.utc))


@dataclass(frozen=True)
class ExistingBooking:
    """Represents an existing confirmed appointment used to calculate schedule adjacency."""
    stylist_id: int
    start_ts: datetime
    end_ts: datetime

    def __post_init__(self):
        """Ensures both interval boundaries are timezone-aware in UTC."""
        if self.start_ts.tzinfo is None:
            object.__setattr__(self, "start_ts", self.start_ts.replace(tzinfo=timezone.utc))
        if self.end_ts.tzinfo is None:
            object.__setattr__(self, "end_ts", self.end_ts.replace(tzinfo=timezone.utc))


@dataclass(frozen=True)
class ScoreBreakdown:
    """Breakdown of individual score components for full auditability and explainability."""
    past_bookings: float = 0.0
    preferred_time: float = 0.0
    specialization: float = 0.0
    adjacent_booking: float = 0.0

    @property
    def total(self) -> float:
        return round(
            self.past_bookings + self.preferred_time + self.specialization + self.adjacent_booking,
            2,
        )


@dataclass(frozen=True)
class ScoredRecommendation:
    """An explainable recommendation candidate ranked by the scoring engine."""
    stylist_id: int
    stylist_name: str
    stylist_specialization: str
    start_ts: datetime
    end_ts: datetime
    duration_min: int
    price: Decimal
    score: float
    score_breakdown: ScoreBreakdown
    reason: str


# ── Helper Evaluators ──

_STOPWORDS = {"and", "&", "the", "for", "with", "service", "treatment", "care"}


def _tokenize(text: str) -> set[str]:
    """Extracts normalized alphanumeric words (length >= 3, excluding stopwords)."""
    words = re.findall(r"[a-zA-Z]{3,}", text.lower())
    return {w for w in words if w not in _STOPWORDS}


def check_specialization_match(
    specialization: str,
    service_name: str,
    service_category: str,
) -> tuple[bool, str]:
    """
    Checks if a stylist's specialization keywords match the service name or category.
    Returns (is_match, matched_keyword).
    """
    spec_norm = specialization.lower().strip()
    cat_norm = service_category.lower().strip()
    srv_norm = service_name.lower().strip()

    # Direct category substring match
    if cat_norm and cat_norm in spec_norm:
        return True, service_category

    # Direct service name substring match
    if srv_norm and (srv_norm in spec_norm or spec_norm in srv_norm):
        return True, specialization

    # Token overlap match (e.g. "Coloring", "Fade", "Balayage", "Beard")
    service_tokens = _tokenize(f"{service_name} {service_category}")
    stylist_tokens = _tokenize(specialization)

    common = service_tokens.intersection(stylist_tokens)
    if common:
        # Pick the most descriptive matched token
        matched_token = sorted(common, key=len, reverse=True)[0]
        return True, matched_token.capitalize()

    return False, ""


def matches_preferred_time(slot_start: datetime, preferred_time: str | None) -> bool:
    """
    Checks whether the slot start time satisfies the user's preferred time.
    Supports categorical windows ('morning', 'afternoon', 'evening') and 'HH:MM'.
    """
    if not preferred_time:
        return False

    pref = preferred_time.strip().lower()
    t = slot_start.time()

    if pref in ("morning", "am"):
        # Morning: 06:00 to 11:59
        return t < time(12, 0)
    elif pref in ("afternoon", "pm"):
        # Afternoon: 12:00 to 16:59
        return time(12, 0) <= t < time(17, 0)
    elif pref in ("evening", "night"):
        # Evening: 17:00 onwards
        return t >= time(17, 0)

    # HH:MM target time check (+/- 60 min tolerance window)
    try:
        parts = pref.split(":")
        target_minutes = int(parts[0]) * 60 + int(parts[1])
        slot_minutes = t.hour * 60 + t.minute
        return abs(slot_minutes - target_minutes) <= 60
    except (ValueError, IndexError):
        return False


def is_adjacent_booking(
    stylist_id: int,
    slot_start: datetime,
    slot_end: datetime,
    existing_bookings: Sequence[ExistingBooking],
    buffer_min: int = 0,
) -> bool:
    """
    Detects if a candidate slot is directly adjacent to an existing booking for that stylist.
    Filling gaps between appointments maximizes salon throughput and minimizes idle wait.
    """
    buffer_delta = timedelta(minutes=buffer_min)
    for b in existing_bookings:
        if b.stylist_id != stylist_id:
            continue
        # Slot ends immediately when an existing booking starts (preceding slot)
        if abs((slot_end - b.start_ts).total_seconds()) <= buffer_delta.total_seconds():
            return True
        # Slot starts immediately when an existing booking ends (succeeding slot)
        if abs((slot_start - b.end_ts).total_seconds()) <= buffer_delta.total_seconds():
            return True
    return False


def build_explanation(
    stylist_name: str,
    past_count: int,
    loyalty_score: float,
    time_score: float,
    preferred_time: str | None,
    spec_score: float,
    matched_spec: str,
    adj_score: float,
) -> str:
    """Builds a plain-language explanation matching earned score components."""
    reasons: list[str] = []

    if loyalty_score > 0:
        times_label = "1 time" if past_count == 1 else f"{past_count} times"
        reasons.append(f"You have booked with {stylist_name} {times_label} before (+{loyalty_score:g})")

    if time_score > 0 and preferred_time:
        reasons.append(f"Fits your {preferred_time.lower()} preference (+{time_score:g})")

    if spec_score > 0 and matched_spec:
        reasons.append(f"{stylist_name} specializes in {matched_spec} (+{spec_score:g})")

    if adj_score > 0:
        reasons.append("Connects with an existing appointment to eliminate idle downtime (+1)")

    if not reasons:
        return "Available appointment slot matching your requested service and date."

    return " • ".join(reasons)


# ── Core Recommendation Algorithm ──

def recommend_slots(
    candidate_slots: Sequence[CandidateSlot],
    service_name: str,
    service_category: str,
    preferred_time: str | None = None,
    past_booking_counts: dict[int, int] | None = None,
    existing_bookings: Sequence[ExistingBooking] | None = None,
    buffer_min: int = 0,
    top_n: int = 3,
) -> list[ScoredRecommendation]:
    """
    Pure Python ranking engine that scores each (stylist, slot) candidate pair.
    
    Scoring criteria:
    1. Loyalty: +3 scaled by past bookings with that stylist (capped at +3.0)
    2. Preferred Time: +2 for slots falling in the preferred time window
    3. Specialization: +1 if stylist specialization matches service name/category
    4. Adjacency: +1 if slot directly touches an existing confirmed booking (gap-filling)
    
    Returns the top N scored slots sorted by score DESC, then start_ts ASC, then stylist_id ASC.
    """
    if not candidate_slots:
        return []

    past_counts = past_booking_counts or {}
    bookings = existing_bookings or []

    scored_items: list[ScoredRecommendation] = []

    for slot in candidate_slots:
        # 1. Past bookings score (+3 max, scaled linearly: 1 booking = +1, 2 = +2, 3+ = +3)
        past_count = past_counts.get(slot.stylist_id, 0)
        loyalty_score = min(3.0, round(float(past_count), 1))

        # 2. Preferred time window score (+2)
        has_time_match = matches_preferred_time(slot.start_ts, preferred_time)
        time_score = 2.0 if has_time_match else 0.0

        # 3. Specialization match score (+1)
        has_spec_match, matched_spec = check_specialization_match(
            slot.stylist_specialization,
            service_name,
            service_category,
        )
        spec_score = 1.0 if has_spec_match else 0.0

        # 4. Adjacent booking gap-filler score (+1)
        has_adj = is_adjacent_booking(
            slot.stylist_id,
            slot.start_ts,
            slot.end_ts,
            bookings,
            buffer_min=buffer_min,
        )
        adj_score = 1.0 if has_adj else 0.0

        breakdown = ScoreBreakdown(
            past_bookings=loyalty_score,
            preferred_time=time_score,
            specialization=spec_score,
            adjacent_booking=adj_score,
        )

        reason = build_explanation(
            stylist_name=slot.stylist_name,
            past_count=past_count,
            loyalty_score=loyalty_score,
            time_score=time_score,
            preferred_time=preferred_time,
            spec_score=spec_score,
            matched_spec=matched_spec,
            adj_score=adj_score,
        )

        duration_min = int((slot.end_ts - slot.start_ts).total_seconds() // 60)

        scored_items.append(
            ScoredRecommendation(
                stylist_id=slot.stylist_id,
                stylist_name=slot.stylist_name,
                stylist_specialization=slot.stylist_specialization,
                start_ts=slot.start_ts,
                end_ts=slot.end_ts,
                duration_min=duration_min,
                price=slot.price,
                score=breakdown.total,
                score_breakdown=breakdown,
                reason=reason,
            )
        )

    # Sort deterministically:
    # 1. Highest score first (-x.score)
    # 2. Earliest start time first (x.start_ts)
    # 3. Stylist ID ascending (x.stylist_id)
    scored_items.sort(key=lambda x: (-x.score, x.start_ts, x.stylist_id))

    return scored_items[:top_n]

