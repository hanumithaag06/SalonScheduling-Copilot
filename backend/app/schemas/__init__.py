# Why: Re-exports all schemas for convenient top-level imports.

from app.schemas.auth import UserRegister, UserLogin, UserOut, TokenResponse
from app.schemas.service import ServiceCreate, ServiceUpdate, ServiceOut
from app.schemas.stylist import StylistCreate, StylistUpdate, StylistOut, StylistServiceAssign
from app.schemas.schedule import WorkingHoursCreate, WorkingHoursOut, TimeOffCreate, TimeOffOut
from app.schemas.slot import SlotOut
from app.schemas.booking import BookingCreate, BookingReschedule, BookingOut

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
]
