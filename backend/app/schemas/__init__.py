# Why: Re-exports all schemas for convenient top-level imports.

from app.schemas.auth import UserRegister, UserLogin, UserOut, TokenResponse
from app.schemas.service import ServiceCreate, ServiceUpdate, ServiceOut
from app.schemas.stylist import StylistCreate, StylistUpdate, StylistOut, StylistServiceAssign
from app.schemas.schedule import WorkingHoursCreate, WorkingHoursOut, TimeOffCreate, TimeOffOut
from app.schemas.slot import SlotOut
from app.schemas.booking import BookingCreate, BookingReschedule, BookingOut
from app.schemas.hold import HoldCreate, HoldOut
from app.schemas.recommend import ScoreBreakdownOut, RecommendationOut
from app.schemas.notification import NotificationOut
from app.schemas.waitlist import WaitlistCreate, WaitlistOut
from app.schemas.admin import (
    DashboardOut,
    AdminBookingOut,
    AdminBookingCreate,
    BookingsPerDay,
    RevenuePerService,
    StylistUtilization,
    PeakHour,
    HeatmapCell,
)
from app.schemas.assistant import (
    AssistantParseRequest,
    AssistantParseResponse,
    AssistantSuggestRequest,
    AssistantSuggestResponse,
)

__all__ = [
    "UserRegister",
    "UserLogin",
    "UserOut",
    "TokenResponse",
    "ServiceCreate",
    "ServiceUpdate",
    "ServiceOut",
    "StylistCreate",
    "StylistUpdate",
    "StylistOut",
    "StylistServiceAssign",
    "WorkingHoursCreate",
    "WorkingHoursOut",
    "TimeOffCreate",
    "TimeOffOut",
    "SlotOut",
    "BookingCreate",
    "BookingReschedule",
    "BookingOut",
    "HoldCreate",
    "HoldOut",
    "ScoreBreakdownOut",
    "RecommendationOut",
    "NotificationOut",
    "WaitlistCreate",
    "WaitlistOut",
    "DashboardOut",
    "AdminBookingOut",
    "AdminBookingCreate",
    "BookingsPerDay",
    "RevenuePerService",
    "StylistUtilization",
    "PeakHour",
    "HeatmapCell",
    "AssistantParseRequest",
    "AssistantParseResponse",
    "AssistantSuggestRequest",
    "AssistantSuggestResponse",
]
