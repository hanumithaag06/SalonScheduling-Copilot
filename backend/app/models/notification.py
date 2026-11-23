# Why: Notification model for customer alerts (email, in-app, 24h reminders).
# Tracks delivery status and connects notifications to relevant bookings.

from datetime import datetime
from sqlalchemy import (
    String, Integer, Text, DateTime, ForeignKey, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    booking_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'booking_confirmed' | 'booking_cancelled' | 'waitlist_offer' | 'reminder_24h'
    message: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(
        String(20), default="in_app", nullable=False
    )  # 'in_app' | 'email'
    status: Mapped[str] = mapped_column(
        String(20), default="unread", nullable=False
    )  # 'unread' | 'read' | 'sent'
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User", back_populates="notifications")
    booking = relationship("Booking", back_populates="notifications")

