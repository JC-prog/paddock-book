from fastapi import APIRouter, Depends, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from src.core.db import get_connection
from src.core.security import get_current_user
from src.modules.chat.schemas import ChatRequest
from src.modules.chat.service import generate_reply, retrieve_context

router = APIRouter()


@router.post("/v1/chat")
async def post_chat(
    chat_request: ChatRequest, user: dict = Depends(get_current_user)
) -> EventSourceResponse:
    conn = get_connection()
    try:
        chunks = retrieve_context(chat_request.message, user["department"], conn=conn)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not retrieve regulation content",
        ) from exc

    return EventSourceResponse(generate_reply(chat_request.message, chunks))
