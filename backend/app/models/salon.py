# Why: Salon management models: Service, Stylist, working schedule, and time-off.
# Captures salon offerings, stylist capabilities, and schedule constraints.

from datetime import datetime, time
from decimal import Decimal
from sqlalchemy import (
    String, Integer, Numeric, Boolean, Time, DateTime,
    ForeignKey, Table, Column, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

# Many-to-Many association table between Stylists and Services
stylist_services = Table(
    "stylist_services",
    Base.metadata,
    Column("stylist_id", Integer, ForeignKey("stylists.id", ondelete="CASCADE"), primary_key=True),
    Column("service_id", Integer, ForeignKey("services.id", ondelete="CASCADE"), primary_key=True),
)


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # Hair, Color, Spa, Nails, etc.
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Stylists capable of performing this service
    stylists = relationship("Stylist", secondary=stylist_services, back_populates="services")
    bookings = relationship("Booking", back_populates="service")


class Stylist(Base):
    __tablename__ = "stylists"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    specialization: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    services = relationship("Service", secondary=stylist_services, back_populates="stylists")
    working_hours = relationship("WorkingHours", back_populates="stylist", cascade="all, delete-orphan")
    time_off = relationship("TimeOff", back_populates="stylist", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="stylist")
    slot_holds = relationship("SlotHold", back_populates="stylist")


class WorkingHours(Base):
    """
    Defines regular weekly shifts per stylist.
    weekday: 0=Monday, 1=Tuesday, ..., 6=Sunday.
    """
    __tablename__ = "working_hours"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stylist_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stylists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 to 6
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    stylist = relationship("Stylist", back_populates="working_hours")


class TimeOff(Base):
    """
    Vacations, leaves, or salon holidays when a stylist is unavailable.
    All timestamps stored in UTC.
    """
    __tablename__ = "time_off"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stylist_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stylists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)

    stylist = relationship("Stylist", back_populates="time_off")
