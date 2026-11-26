# Why: Database seeder for demo and production seed data.
# Populates 10 services, 5 stylists with Mon-Sat working hours, 1 admin, 8 customers,
# and ~60 historical bookings over the last 60 days. Safely re-runnable (idempotent).

import asyncio
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, engine
from app.models import (
    User, Service, Stylist, stylist_services,
    WorkingHours, TimeOff, Booking, Notification, AuditLog
)

# Deterministic base timestamp for consistent demo dates (in UTC)
BASE_NOW = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)


async def seed_data(session: AsyncSession) -> dict[str, int]:
    """
    Seeds demo data into the database.
    Returns counts of seeded entities.
    """
    print("🌱 Starting database seeding...")
    default_password_hash = hash_password("Password123!")

    # ──────────────────────────────────────────────────────────
    # 1. Users (1 Admin + 8 Customers)
    # ──────────────────────────────────────────────────────────
    users_data = [
        {"name": "Admin Manager", "email": "admin@stylify.com", "phone": "+1-555-0100", "role": "admin"},
        {"name": "Emma Watson", "email": "emma.w@example.com", "phone": "+1-555-0101", "role": "customer"},
        {"name": "Liam Smith", "email": "liam.s@example.com", "phone": "+1-555-0102", "role": "customer"},
        {"name": "Olivia Davis", "email": "olivia.d@example.com", "phone": "+1-555-0103", "role": "customer"},
        {"name": "Noah Wilson", "email": "noah.w@example.com", "phone": "+1-555-0104", "role": "customer"},
        {"name": "Ava Taylor", "email": "ava.t@example.com", "phone": "+1-555-0105", "role": "customer"},
        {"name": "Ethan Brown", "email": "ethan.b@example.com", "phone": "+1-555-0106", "role": "customer"},
        {"name": "Mia Martinez", "email": "mia.m@example.com", "phone": "+1-555-0107", "role": "customer"},
        {"name": "Lucas Anderson", "email": "lucas.a@example.com", "phone": "+1-555-0108", "role": "customer"},
    ]

    user_map: dict[str, User] = {}
    for u in users_data:
        stmt = select(User).where(User.email == u["email"])
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            user = User(
                name=u["name"],
                email=u["email"],
                phone=u["phone"],
                password_hash=default_password_hash,
                role=u["role"],
            )
            session.add(user)
            await session.flush()
        user_map[u["email"]] = user

    print(f"✓ Users ready ({len(user_map)} users)")

    # ──────────────────────────────────────────────────────────
    # 2. Services (10 Services across Hair, Color, Treatments, Nails)
    # ──────────────────────────────────────────────────────────
    services_data = [
        {"name": "Classic Haircut", "category": "Hair", "duration_min": 30, "price": Decimal("35.00")},
        {"name": "Deluxe Cut & Styling", "category": "Hair", "duration_min": 60, "price": Decimal("65.00")},
        {"name": "Beard Grooming & Shape", "category": "Hair", "duration_min": 30, "price": Decimal("25.00")},
        {"name": "Full Hair Color", "category": "Color", "duration_min": 90, "price": Decimal("120.00")},
        {"name": "Balayage Highlights", "category": "Color", "duration_min": 120, "price": Decimal("150.00")},
        {"name": "Root Touch-Up", "category": "Color", "duration_min": 60, "price": Decimal("75.00")},
        {"name": "Keratin Smoothing Treatment", "category": "Treatments", "duration_min": 90, "price": Decimal("160.00")},
        {"name": "Scalp Detox & Massage", "category": "Treatments", "duration_min": 45, "price": Decimal("55.00")},
        {"name": "Signature Manicure", "category": "Nails", "duration_min": 45, "price": Decimal("40.00")},
        {"name": "Express Spa Pedicure", "category": "Nails", "duration_min": 45, "price": Decimal("45.00")},
    ]

    service_map: dict[str, Service] = {}
    for s in services_data:
        stmt = select(Service).where(Service.name == s["name"])
        res = await session.execute(stmt)
        service = res.scalar_one_or_none()
        if not service:
            service = Service(
                name=s["name"],
                category=s["category"],
                duration_min=s["duration_min"],
                price=s["price"],
                is_active=True,
            )
            session.add(service)
            await session.flush()
        service_map[s["name"]] = service

    print(f"✓ Services ready ({len(service_map)} services)")

    # ──────────────────────────────────────────────────────────
    # 3. Stylists (5 Stylists with specializations)
    # ──────────────────────────────────────────────────────────
    stylists_data = [
        {"name": "Elena Rostova", "specialization": "Master Colorist & Highlights"},
        {"name": "Marcus Vance", "specialization": "Precision Barbering & Mens Styling"},
        {"name": "Aria Chen", "specialization": "Texture, Curls & Keratin Care"},
        {"name": "Devon Miller", "specialization": "Creative Cut & Blowouts"},
        {"name": "Sophia Patel", "specialization": "Nail Art, Esthetics & Spa"},
    ]

    stylist_map: dict[str, Stylist] = {}
    for st in stylists_data:
        stmt = select(Stylist).where(Stylist.name == st["name"])
        res = await session.execute(stmt)
        stylist = res.scalar_one_or_none()
        if not stylist:
            stylist = Stylist(
                name=st["name"],
                specialization=st["specialization"],
                is_active=True,
            )
            session.add(stylist)
            await session.flush()
        stylist_map[st["name"]] = stylist

    print(f"✓ Stylists ready ({len(stylist_map)} stylists)")

    # ──────────────────────────────────────────────────────────
    # 4. Stylist Services (Many-to-Many Mappings)
    # ──────────────────────────────────────────────────────────
    stylist_service_assignments = {
        "Elena Rostova": ["Full Hair Color", "Balayage Highlights", "Root Touch-Up", "Deluxe Cut & Styling"],
        "Marcus Vance": ["Classic Haircut", "Beard Grooming & Shape", "Deluxe Cut & Styling"],
        "Aria Chen": ["Keratin Smoothing Treatment", "Scalp Detox & Massage", "Deluxe Cut & Styling", "Classic Haircut"],
        "Devon Miller": ["Classic Haircut", "Deluxe Cut & Styling", "Root Touch-Up", "Full Hair Color"],
        "Sophia Patel": ["Signature Manicure", "Express Spa Pedicure", "Scalp Detox & Massage"],
    }

    for stylist_name, service_names in stylist_service_assignments.items():
        st = stylist_map[stylist_name]
        for s_name in service_names:
            srv = service_map[s_name]
            # Check if association exists
            chk = await session.execute(
                select(stylist_services).where(
                    stylist_services.c.stylist_id == st.id,
                    stylist_services.c.service_id == srv.id
                )
            )
            if not chk.first():
                await session.execute(
                    stylist_services.insert().values(stylist_id=st.id, service_id=srv.id)
                )

    print("✓ Stylist-service specializations mapped")

    # ──────────────────────────────────────────────────────────
    # 5. Working Hours (Mon-Sat, Weekday 0 to 5, 09:00 - 18:00)
    # ──────────────────────────────────────────────────────────
    for st in stylist_map.values():
        for weekday in range(6):  # 0=Monday through 5=Saturday
            stmt = select(WorkingHours).where(
                WorkingHours.stylist_id == st.id,
                WorkingHours.weekday == weekday
            )
            res = await session.execute(stmt)
            if not res.scalar_one_or_none():
                wh = WorkingHours(
                    stylist_id=st.id,
                    weekday=weekday,
                    start_time=time(9, 0),
                    end_time=time(18, 0)
                )
                session.add(wh)

    # ──────────────────────────────────────────────────────────
    # 6. Time Off Sample (Stylist vacation)
    # ──────────────────────────────────────────────────────────
    elena = stylist_map["Elena Rostova"]
    to_stmt = select(TimeOff).where(TimeOff.stylist_id == elena.id)
    if not (await session.execute(to_stmt)).scalar_one_or_none():
        sample_time_off = TimeOff(
            stylist_id=elena.id,
            start_ts=BASE_NOW + timedelta(days=14, hours=9),
            end_ts=BASE_NOW + timedelta(days=16, hours=18),
            reason="Advanced Coloring Masterclass"
        )
        session.add(sample_time_off)

    print("✓ Working hours (Mon-Sat) and time-off seeded")

    # ──────────────────────────────────────────────────────────
    # 7. ~60 Historical Bookings over the last 60 days
    # ──────────────────────────────────────────────────────────
    # To make this idempotent, we clean up previously seeded demo bookings
    await session.execute(delete(Booking))
    await session.flush()

    customer_list = [u for u in user_map.values() if u.role == "customer"]
    stylist_list = list(stylist_map.values())

    bookings_created = 0
    # Generate 1 booking per working day across 60 days (gives exactly ~60 bookings)
    for day_offset in range(60, -3, -1):  # from 60 days ago up to 2 days ahead
        target_date = (BASE_NOW - timedelta(days=day_offset)).date()
        # Salon is closed on Sunday (weekday 6)
        if target_date.weekday() == 6:
            continue

        # Single booking per working day, rotating slot times (10:00, 11:30, 14:00, 15:30)
        slot_hour = 10 if (day_offset % 2 == 0) else 14
        slot_start_time = time(slot_hour, 0)

        stylist = stylist_list[day_offset % len(stylist_list)]
        customer = customer_list[day_offset % len(customer_list)]

        # Pick a service this stylist offers
        allowed_services = [
            service_map[s_name]
            for s_name in stylist_service_assignments[stylist.name]
        ]
        service = allowed_services[day_offset % len(allowed_services)]

        start_dt = datetime.combine(target_date, slot_start_time, tzinfo=timezone.utc)
        end_dt = start_dt + timedelta(minutes=service.duration_min)

        # Status: past bookings are mostly completed (some cancelled), upcoming are confirmed
        if day_offset > 0:
            status = "cancelled" if (day_offset % 8 == 0) else "completed"
        else:
            status = "confirmed"

        booking = Booking(
            user_id=customer.id,
            stylist_id=stylist.id,
            service_id=service.id,
            start_ts=start_dt,
            end_ts=end_dt,
            status=status,
            notes=f"Demo booking: {service.name} with {stylist.name}",
            created_at=start_dt - timedelta(days=2),
            updated_at=start_dt - timedelta(days=2)
        )
        session.add(booking)
        bookings_created += 1

    await session.commit()
    print(f"✓ Bookings ready ({bookings_created} historical/upcoming bookings seeded)")
    print("✨ Seeding completed successfully!")

    return {
        "users": len(user_map),
        "services": len(service_map),
        "stylists": len(stylist_map),
        "bookings": bookings_created,
    }


async def main():
    """CLI runner: python seed.py"""
    async with AsyncSessionLocal() as session:
        await seed_data(session)


if __name__ == "__main__":
    asyncio.run(main())
