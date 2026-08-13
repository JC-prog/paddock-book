import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from src.core.db import get_connection
from src.core.security import get_current_user
from src.modules.chat.schemas import ChatRequest
from src.modules.chat.service import generate_reply, resolve_provider_config, retrieve_context

logger = logging.getLogger(__name__)

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

    logger.info(
        "chat retrieval succeeded",
        extra={
            "event": "chat_retrieval_succeeded",
            "user_id": user["sub"],
            "departments": [user["department"]],
        },
    )

    # A second, short-lived connection — kept separate from
    # retrieve_context's (already closed above) so no DB connection is
    # held open for the duration of the SSE stream itself.
    config_conn = get_connection()
    try:
        provider_config = resolve_provider_config(conn=config_conn)
    finally:
        config_conn.close()

    return EventSourceResponse(generate_reply(chat_request.message, chunks, provider_config=provider_config))
