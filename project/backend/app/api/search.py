from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.db import get_db
from app.schemas.search import SearchRequest
from app.services.search import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=dict)
async def search(
    data: SearchRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    svc = SearchService(db)
    try:
        hits = await svc.search(user_id, data)
    except Exception as e:
        raise HTTPException(status_code=422, detail={"code": "search_error", "message": str(e)})
    return {"items": [h.model_dump() for h in hits]}
