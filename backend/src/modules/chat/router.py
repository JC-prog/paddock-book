from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from src.modules.chat.schemas import ChatRequest
from src.modules.chat.service import generate_placeholder_reply

router = APIRouter()


@router.post("/v1/chat")
async def post_chat(chat_request: ChatRequest) -> EventSourceResponse:
    return EventSourceResponse(generate_placeholder_reply())
