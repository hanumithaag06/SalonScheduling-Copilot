# Why: Waitlist model for handling cancellations and slot cascading.
# When a confirmed booking is cancelled, waitlisted users are notified in order.

from datetime import date, datetime
from sqlalchemy import (
    String, Integer, Date, DateTime, ForeignKey, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Waitlist(Base):
    __tablename__ = "waitlist"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    service_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stylist_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("stylists.id", ondelete="SET NULL"), nullable=True, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    time_pref: Mapped[str] = mapped_column(String(50), nullable=False)  # 'morning' | 'afternoon' | 'evening' | 'any'
    status: Mapped[str] = mapped_column(
        String(20), default="waiting", nullable=False, index=True
    )  # 'waiting' | 'offered' | 'claimed' | 'expired'
    offered_slot_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    offer_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User", back_populates="waitlist_entries")
    service = relationship("Service")
    stylist = relationship("Stylist")

