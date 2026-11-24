# Why: Endpoints for salon services.
# Public read for browsing; admin-only creation, modification, and deletion.

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.core.errors import NotFoundException
from app.db.session import get_db
from app.models import Service, User
from app.schemas.service import ServiceCreate, ServiceUpdate, ServiceOut

router = APIRouter(prefix="/services", tags=["services"])


@router.get("", response_model=list[ServiceOut])
async def list_services(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """List salon services. Defaults to active services only."""
    stmt = select(Service)
    if active_only:
        stmt = stmt.where(Service.is_active.is_(True))
    stmt = stmt.order_by(Service.category, Service.name)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{service_id}", response_model=ServiceOut)
async def get_service(service_id: int, db: AsyncSession = Depends(get_db)):
    """Get single service by ID."""
    stmt = select(Service).where(Service.id == service_id)
    service = (await db.execute(stmt)).scalar_one_or_none()
    if not service:
        raise NotFoundException(detail="Service not found", code="SERVICE_NOT_FOUND")
    return service


@router.post("", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
async def create_service(
    payload: ServiceCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: Create a new service."""
    service = Service(
        name=payload.name,
        category=payload.category,
        duration_min=payload.duration_min,
        price=payload.price,
        is_active=payload.is_active,
    )
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return service


@router.put("/{service_id}", response_model=ServiceOut)
async def update_service(
    service_id: int,
    payload: ServiceUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: Update service details."""
    stmt = select(Service).where(Service.id == service_id)
    service = (await db.execute(stmt)).scalar_one_or_none()
    if not service:
        raise NotFoundException(detail="Service not found", code="SERVICE_NOT_FOUND")

    for field, val in payload.model_dump(exclude_unset=True).items():
        setattr(service, field, val)

    await db.commit()
    await db.refresh(service)
    return service


@router.delete("/{service_id}")
async def delete_service(
    service_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: Soft-delete service by marking is_active=False."""
    stmt = select(Service).where(Service.id == service_id)
    service = (await db.execute(stmt)).scalar_one_or_none()
    if not service:
        raise NotFoundException(detail="Service not found", code="SERVICE_NOT_FOUND")

    service.is_active = False
    await db.commit()
    return {"detail": "Service deactivated successfully", "code": "SERVICE_DEACTIVATED"}

