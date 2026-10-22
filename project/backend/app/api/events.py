from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.db import get_db
from app.schemas.events import EventCreate, EventPatch, EventRead
from app.services.events import ConflictError, EventService, NotFoundError, ValidationError

router = APIRouter(prefix="/events", tags=["events"])


def _svc(db):
    return EventService(db)


@router.get("", response_model=list[EventRead])
async def list_events(
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None, alias="to"),
    type: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    from datetime import datetime
    def parse(v):
        if v is None:
            return None
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception:
            return None
    svc = _svc(db)
    return await svc.list(user_id, from_=parse(from_), to=parse(to), type=type)


@router.post("", response_model=EventRead, status_code=201)
async def create_event(
    data: EventCreate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    svc = _svc(db)
    try:
        return await svc.create(user_id, data)
    except ConflictError as e:
        raise HTTPException(status_code=409, detail={"code": "meeting_overlap", "message": str(e)})
    except ValidationError as e:
        raise HTTPException(status_code=422, detail={"code": "validation_error", "message": str(e)})
    except ValueError as e:
        raise HTTPException(status_code=422, detail={"code": "validation_error", "message": str(e)})


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    svc = _svc(db)
    try:
        return await svc.get(user_id, event_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "event not found"})


@router.patch("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: UUID,
    data: EventPatch,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    svc = _svc(db)
    try:
        return await svc.update(user_id, event_id, data)
    except NotFoundError:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "event not found"})
    except ConflictError as e:
        raise HTTPException(status_code=409, detail={"code": "meeting_overlap", "message": str(e)})


@router.post("/{event_id}/complete", response_model=EventRead)
async def complete_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    svc = _svc(db)
    try:
        return await svc.complete(user_id, event_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "event not found"})


@router.delete("/{event_id}", status_code=204)
async def delete_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    svc = _svc(db)
    try:
        await svc.delete(user_id, event_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "event not found"})
