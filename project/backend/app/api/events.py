from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from pydantic import AwareDatetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.db import get_db
from app.schemas.events import (
    EventCreate,
    EventPatch,
    EventRead,
    EventStatus,
    EventType,
)
from app.services.events import EventService

router = APIRouter(prefix="/events", tags=["events"])


def _svc(db: AsyncSession) -> EventService:
    return EventService(db)


@router.get("", response_model=list[EventRead])
async def list_events(
    from_: AwareDatetime | None = Query(default=None, alias="from"),
    to: AwareDatetime | None = Query(default=None),
    type: EventType | None = Query(default=None),
    status: EventStatus | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    return await _svc(db).list(
        user_id,
        start=from_,
        end=to,
        type=type,
        status=status,
    )


@router.post("", response_model=EventRead, status_code=201)
async def create_event(
    data: EventCreate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    return await _svc(db).create(user_id, data)


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    return await _svc(db).get(user_id, event_id)


@router.patch("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: UUID,
    data: EventPatch,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    return await _svc(db).update(user_id, event_id, data)


@router.post("/{event_id}/complete", response_model=EventRead)
async def complete_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    return await _svc(db).complete(user_id, event_id)


@router.delete("/{event_id}", status_code=204)
async def delete_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    await _svc(db).delete(user_id, event_id)
    return Response(status_code=204)
