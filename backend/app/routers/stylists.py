# Why: Endpoints for salon stylists and their service specializations.
# Public read; admin-only creation, modification, and service assignments.

from fastapi import APIRouter, Depends, status
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.core.errors import NotFoundException
from app.db.session import get_db
from app.models import Stylist, Service, stylist_services, User
from app.schemas.stylist import StylistCreate, StylistUpdate, StylistOut, StylistServiceAssign

router = APIRouter(prefix="/stylists", tags=["stylists"])


@router.get("", response_model=list[StylistOut])
async def list_stylists(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """List all stylists with their mapped services."""
    stmt = select(Stylist).options(selectinload(Stylist.services))
    if active_only:
        stmt = stmt.where(Stylist.is_active.is_(True))
    stmt = stmt.order_by(Stylist.name)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{stylist_id}", response_model=StylistOut)
async def get_stylist(stylist_id: int, db: AsyncSession = Depends(get_db)):
    """Get stylist by ID including services offered."""
    stmt = select(Stylist).options(selectinload(Stylist.services)).where(Stylist.id == stylist_id)
    stylist = (await db.execute(stmt)).scalar_one_or_none()
    if not stylist:
        raise NotFoundException(detail="Stylist not found", code="STYLIST_NOT_FOUND")
    return stylist


@router.post("", response_model=StylistOut, status_code=status.HTTP_201_CREATED)
async def create_stylist(
    payload: StylistCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: Create a new stylist and optionally assign services."""
    stylist = Stylist(
        name=payload.name,
        specialization=payload.specialization,
        is_active=payload.is_active,
    )
    db.add(stylist)
    await db.flush()

    if payload.service_ids:
        for sid in payload.service_ids:
            await db.execute(stylist_services.insert().values(stylist_id=stylist.id, service_id=sid))

    await db.commit()
    # Re-fetch with loaded services
    stmt = select(Stylist).options(selectinload(Stylist.services)).where(Stylist.id == stylist.id)
    return (await db.execute(stmt)).scalar_one()


@router.put("/{stylist_id}", response_model=StylistOut)
async def update_stylist(
    stylist_id: int,
    payload: StylistUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: Update stylist information and service assignments."""
    stmt = select(Stylist).options(selectinload(Stylist.services)).where(Stylist.id == stylist_id)
    stylist = (await db.execute(stmt)).scalar_one_or_none()
    if not stylist:
        raise NotFoundException(detail="Stylist not found", code="STYLIST_NOT_FOUND")

    data = payload.model_dump(exclude_unset=True)
    service_ids = data.pop("service_ids", None)

    for field, val in data.items():
        setattr(stylist, field, val)

    if service_ids is not None:
        await db.execute(delete(stylist_services).where(stylist_services.c.stylist_id == stylist_id))
        for sid in service_ids:
            await db.execute(stylist_services.insert().values(stylist_id=stylist_id, service_id=sid))

    await db.commit()
    stmt = select(Stylist).options(selectinload(Stylist.services)).where(Stylist.id == stylist_id)
    return (await db.execute(stmt)).scalar_one()


@router.delete("/{stylist_id}")
async def delete_stylist(
    stylist_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: Soft-delete stylist by marking is_active=False."""
    stmt = select(Stylist).where(Stylist.id == stylist_id)
    stylist = (await db.execute(stmt)).scalar_one_or_none()
    if not stylist:
        raise NotFoundException(detail="Stylist not found", code="STYLIST_NOT_FOUND")

    stylist.is_active = False
    await db.commit()
    return {"detail": "Stylist deactivated successfully", "code": "STYLIST_DEACTIVATED"}


@router.post("/{stylist_id}/services", response_model=StylistOut)
async def assign_stylist_services(
    stylist_id: int,
    payload: StylistServiceAssign,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: Overwrite service mappings for a stylist."""
    stmt = select(Stylist).where(Stylist.id == stylist_id)
    stylist = (await db.execute(stmt)).scalar_one_or_none()
    if not stylist:
        raise NotFoundException(detail="Stylist not found", code="STYLIST_NOT_FOUND")

    # Replace service associations
    await db.execute(delete(stylist_services).where(stylist_services.c.stylist_id == stylist_id))
    for sid in payload.service_ids:
        await db.execute(stylist_services.insert().values(stylist_id=stylist_id, service_id=sid))

    await db.commit()
    res = await db.execute(
        select(Stylist).options(selectinload(Stylist.services)).where(Stylist.id == stylist_id)
    )
    return res.scalar_one()
