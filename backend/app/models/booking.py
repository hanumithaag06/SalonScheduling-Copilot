# Why: Booking and temporary slot reservation models.
# Handles customer appointments and the 5-minute pre-booking hold mechanism.

from datetime import datetime
from sqlalchemy import (
    String, Integer, Text, DateTime, ForeignKey, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Booking(Base):
    """
    Core appointment entity.
    Protected by PostgreSQL btree_gist exclusion constraint on (stylist_id, [start_ts, end_ts))
    for status='confirmed' to prevent double booking at the database level.
    """
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    service_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stylist_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stylists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), default="confirmed", nullable=False, index=True
    )  # 'confirmed' | 'cancelled' | 'completed'
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="bookings")
    service = relationship("Service", back_populates="bookings")
    stylist = relationship("Stylist", back_populates="bookings")
    notifications = relationship("Notification", back_populates="booking")


class SlotHold(Base):
    """
    Temporary 5-minute lock on a slot while a customer completes booking details.
    Prevents race conditions where two users attempt to book the same slot simultaneously.
    """
    __tablename__ = "slot_holds"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stylist_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stylists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    user = relationship("User", back_populates="slot_holds")
    stylist = relationship("Stylist", back_populates="slot_holds")

