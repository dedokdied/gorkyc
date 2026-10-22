from fastapi import APIRouter

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def chat():
    return {"session_id": None, "reply": "not implemented", "action": None, "clarification": None, "audio_url": None}
