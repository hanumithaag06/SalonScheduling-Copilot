# Why: Pure computational intent and entity extraction parser for the salon assistant.
# Uses rapidfuzz for fuzzy service matching and dateparser for natural language dates.
# Contains zero DB/HTTP dependencies so it can be tested in isolation.

from dataclasses import dataclass, field
from datetime import date as date_type, datetime, time, timedelta, timezone
from decimal import Decimal
import re
from typing import Sequence

from dateparser.search import search_dates
from rapidfuzz import fuzz


# Canonical salon synonyms mapping for accurate intent extraction
SERVICE_SYNONYMS: dict[str, list[str]] = {
    "classic haircut": [
        "haircut", "hair cut", "cut", "classic cut", "men haircut", "women haircut",
        "hair trimming", "trim", "mens haircut", "womens haircut", "fade", "buzz cut",
        "standard haircut", "normal haircut", "haircuts", "hair cuts"
    ],
    "deluxe cut & styling": [
        "deluxe cut", "styling", "cut and style", "blowout", "wash and cut",
        "blow out", "style", "hair styling", "deluxe haircut", "wash and blow dry",
        "wash and style", "blowdry", "hair blowout"
    ],
    "beard grooming & shape": [
        "beard trim", "beard grooming", "beard", "shave", "beard shape", "mustache",
        "beard styling", "facial hair", "shaving", "moustache"
    ],
    "full hair color": [
        "hair color", "color", "hair dye", "coloring", "full color", "dye",
        "dye hair", "coloring hair", "single process", "hair colour", "colour", "hair coloring"
    ],
    "balayage highlights": [
        "balayage", "highlights", "ombre", "foils", "highlight", "streaks", "blonde balayage"
    ],
    "root touch-up": [
        "root touchup", "roots", "touch up", "root touch-up", "root touch up", "gray coverage"
    ],
    "keratin smoothing treatment": [
        "keratin", "smoothing", "brazilian blowout", "keratin treatment",
        "straightening", "hair treatment", "keratin therapy"
    ],
    "scalp detox & massage": [
        "scalp massage", "scalp detox", "head massage", "scalp treatment",
        "head detox", "hair spa", "massage", "scalp care"
    ],
    "signature manicure": [
        "manicure", "mani", "nails", "gel manicure", "nail art", "nail care", "manicures"
    ],
    "express spa pedicure": [
        "pedicure", "pedi", "foot spa", "spa pedicure", "feet spa", "toenails", "pedicures"
    ],
}

# Standard catalogue of salon service catalog items for fallback fuzzy matching
DEFAULT_SERVICE_CATALOG = [
    {"id": 1, "name": "Classic Haircut", "aliases": SERVICE_SYNONYMS["classic haircut"]},
    {"id": 2, "name": "Deluxe Cut & Styling", "aliases": SERVICE_SYNONYMS["deluxe cut & styling"]},
    {"id": 3, "name": "Beard Grooming & Shape", "aliases": SERVICE_SYNONYMS["beard grooming & shape"]},
    {"id": 4, "name": "Full Hair Color", "aliases": SERVICE_SYNONYMS["full hair color"]},
    {"id": 5, "name": "Balayage Highlights", "aliases": SERVICE_SYNONYMS["balayage highlights"]},
    {"id": 6, "name": "Root Touch-Up", "aliases": SERVICE_SYNONYMS["root touch-up"]},
    {"id": 7, "name": "Keratin Smoothing Treatment", "aliases": SERVICE_SYNONYMS["keratin smoothing treatment"]},
    {"id": 8, "name": "Scalp Detox & Massage", "aliases": SERVICE_SYNONYMS["scalp detox & massage"]},
    {"id": 9, "name": "Signature Manicure", "aliases": SERVICE_SYNONYMS["signature manicure"]},
    {"id": 10, "name": "Express Spa Pedicure", "aliases": SERVICE_SYNONYMS["express spa pedicure"]},
]


@dataclass(frozen=True)
class ExtractedIntent:
    """Standardized entity extraction container parsed from natural language."""
    service_name: str | None = None
    service_id: int | None = None
    date: date_type | None = None
    time_pref: str | None = None
    max_price: Decimal | None = None
    missing_fields: list[str] = field(default_factory=list)
    follow_up_question: str | None = None


def extract_budget(text: str) -> Decimal | None:
    """
    Extracts numerical price or budget constraints like '$50', 'under 100', 'max 80'.
    """
    patterns = [
        r"(?:under|below|max|budget|within|less than|\$)\s*(\d+(?:\.\d{2})?)",
        r"(\d+(?:\.\d{2})?)\s*(?:dollars|bucks|usd|\$)",
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            try:
                val = Decimal(match.group(1))
                if val > 0:
                    return val
            except Exception:
                continue
    return None


def extract_time_preference(text: str) -> str | None:
    """
    Extracts time of day preferences: 'morning', 'afternoon', 'evening', or specific HH:MM.
    Checks clock times first to avoid misclassifying '10:30 am' as generic 'morning'.
    """
    lower = text.lower()

    # Specific clock time: e.g. 10:30 am, 2:30pm, 14:00, 10:00
    time_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", lower)
    if time_match and (time_match.group(2) or time_match.group(3)):
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        meridiem = time_match.group(3)
        if meridiem == "pm" and hour < 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"

    if re.search(r"\b(morning|am)\b", lower):
        return "morning"
    if re.search(r"\b(afternoon|midday|noon|pm)\b", lower):
        return "afternoon"
    if re.search(r"\b(evening|night)\b", lower):
        return "evening"

    return None


def extract_service(
    text: str,
    catalog: list[dict] | None = None,
    threshold: float = 75.0,
) -> tuple[str | None, int | None]:
    """
    Fuzzy matches text against the service catalogue using whole-word check
    and rapidfuzz token_set_ratio.
    """
    services = catalog or DEFAULT_SERVICE_CATALOG
    lower = text.lower()

    # 1. Whole-word / phrase match first (sorted by candidate length descending)
    # This ensures specific, longer phrases like "deluxe cut & styling" or "deluxe cut and styling"
    # match before shorter aliases like "cut" or "styling".
    all_candidates: list[tuple[str, str, int]] = []
    for item in services:
        name_lower = item["name"].lower().strip()
        synonyms = SERVICE_SYNONYMS.get(name_lower, [])
        candidates = [item["name"]] + item.get("aliases", []) + synonyms
        # Deduplicate candidates
        seen = set()
        unique_cands = []
        for cand in candidates:
            cl = cand.lower().strip()
            if cl and cl not in seen:
                seen.add(cl)
                unique_cands.append(cand)

        for cand in unique_cands:
            all_candidates.append((cand, item["name"], item["id"]))
            if "&" in cand:
                all_candidates.append((cand.replace("&", "and"), item["name"], item["id"]))

    all_candidates.sort(key=lambda x: len(x[0]), reverse=True)

    for cand, srv_name, srv_id in all_candidates:
        pattern = r"\b" + re.escape(cand.lower()) + r"\b"
        if re.search(pattern, lower):
            return srv_name, srv_id

    # 2. Token set fuzzy match
    best_match = None
    best_score = 0.0

    for item in services:
        name_lower = item["name"].lower().strip()
        synonyms = SERVICE_SYNONYMS.get(name_lower, [])
        candidates = [item["name"]] + item.get("aliases", []) + synonyms
        for cand in candidates:
            score = fuzz.token_set_ratio(cand.lower(), lower)
            if score > best_score and score >= threshold:
                best_score = score
                best_match = (item["name"], item["id"])

    if best_match:
        return best_match[0], best_match[1]

    # 3. Direct keyword heuristics fallback
    keyword_map = [
        ("haircut", "Classic Haircut"),
        ("hair cut", "Classic Haircut"),
        ("cut", "Classic Haircut"),
        ("styling", "Deluxe Cut & Styling"),
        ("blowout", "Deluxe Cut & Styling"),
        ("color", "Full Hair Color"),
        ("colour", "Full Hair Color"),
        ("dye", "Full Hair Color"),
        ("beard", "Beard Grooming & Shape"),
        ("shave", "Beard Grooming & Shape"),
        ("balayage", "Balayage Highlights"),
        ("highlight", "Balayage Highlights"),
        ("highlights", "Balayage Highlights"),
        ("root", "Root Touch-Up"),
        ("keratin", "Keratin Smoothing Treatment"),
        ("scalp", "Scalp Detox & Massage"),
        ("massage", "Scalp Detox & Massage"),
        ("manicure", "Signature Manicure"),
        ("pedicure", "Express Spa Pedicure"),
        ("nail", "Signature Manicure"),
        ("nails", "Signature Manicure"),
    ]
    for kw, target_name in keyword_map:
        if re.search(r"\b" + re.escape(kw) + r"\b", lower):
            for item in services:
                if item["name"].lower() == target_name.lower():
                    return item["name"], item["id"]

    return None, None


def extract_date(
    text: str,
    reference_now: datetime | None = None,
) -> date_type | None:
    """
    Extracts dates using dateparser search_dates with future preference.
    Rejects past dates relative to reference_now.
    """
    now = reference_now or datetime.now(timezone.utc)
    now_date = now.date()

    # 1. Direct ISO date YYYY-MM-DD regex check
    iso_match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if iso_match:
        try:
            d = date_type(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
            if d >= now_date:
                return d
        except ValueError:
            pass

    # 2. Clean price tokens that confuse dateparser (e.g. '$50', 'under 100')
    cleaned = re.sub(r"(?:under|budget|max|dollars|bucks|\$)\s*\d+(?:\.\d{2})?", "", text, flags=re.I)

    # 3. Use search_dates to extract date expressions inside natural language
    try:
        found = search_dates(
            cleaned,
            languages=["en"],
            settings={
                "PREFER_DATES_FROM": "future",
                "RELATIVE_BASE": datetime.combine(now_date, time(0, 0)),
                "RETURN_AS_TIMEZONE_AWARE": False,
            },
        )
        if found:
            for _, dt_found in found:
                p_date = dt_found.date()
                if p_date >= now_date:
                    return p_date
    except Exception:
        pass

    return None


def parse_booking_intent(
    text: str,
    catalog: list[dict] | None = None,
    reference_now: datetime | None = None,
) -> ExtractedIntent:
    """
    Pure Python parser extracting {service, date, time_pref, max_price, missing_fields}.
    If mandatory fields (service or date) are absent, generates a helpful follow-up question.
    """
    now = reference_now or datetime.now(timezone.utc)
    service_name, service_id = extract_service(text, catalog=catalog)
    target_date = extract_date(text, reference_now=now)
    time_pref = extract_time_preference(text)
    budget = extract_budget(text)

    missing: list[str] = []
    if not service_name:
        missing.append("service")
    if not target_date:
        missing.append("date")

    follow_up: str | None = None
    if "service" in missing and "date" in missing:
        follow_up = "What service would you like to book, and on what date? (e.g. 'Haircut tomorrow afternoon')"
    elif "service" in missing:
        date_str = target_date.strftime("%Y-%m-%d") if target_date else "that day"
        follow_up = f"Which salon service would you like to book for {date_str}? We offer haircuts, styling, coloring, and treatments."
    elif "date" in missing:
        follow_up = f"What date would you like to schedule your {service_name}? (e.g. 'tomorrow', 'next Monday', or '2026-12-05')"

    return ExtractedIntent(
        service_name=service_name,
        service_id=service_id,
        date=target_date,
        time_pref=time_pref,
        max_price=budget,
        missing_fields=missing,
        follow_up_question=follow_up,
    )
