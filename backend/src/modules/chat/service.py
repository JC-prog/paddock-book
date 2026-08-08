import psycopg

from src.core import embeddings as embeddings_module
from src.core.config import Settings
from src.modules.chat import generation as generation_module
from src.modules.chat import retrieval as retrieval_module
from src.modules.chat.generation import NO_RELEVANT_INFO_REPLY


def retrieve_context(
    question: str,
    department: str,
    *,
    conn,
    settings_factory=Settings,
    embeddings=embeddings_module,
    retrieval=retrieval_module,
) -> list[dict]:
    """Runs before any SSE stream opens, so a retrieval/embedding failure
    surfaces as a clean error response — not a broken mid-stream connection
    (contracts/chat-api.md's "LLM provider failure" guarantee)."""
    settings = settings_factory()
    try:
        query_embedding = embeddings.embed(
            question,
            provider=settings.embedding_provider,
            region_name=settings.aws_region,
            ollama_host=settings.ollama_host,
            ollama_model=settings.ollama_embedding_model,
        )
        return retrieval.retrieve_relevant_chunks(conn, department, query_embedding)
    except psycopg.Error as exc:
        # Normalize alongside core/embeddings.py's Bedrock-failure wrapping so
        # the router's single `except RuntimeError` covers both failure modes
        # the contract promises a 502 for (embedding call or DB unreachable).
        raise RuntimeError(f"Database retrieval failed: {exc}") from exc
    finally:
        conn.close()


async def generate_reply(
    question: str,
    chunks: list[dict],
    *,
    settings_factory=Settings,
    generation=generation_module,
):
    if not chunks:
        # Deterministic short-circuit (FR-005) — the requester's department
        # has no ingested content at all, so there's nothing to guess from;
        # skip the LLM call entirely rather than relying on it to refuse.
        yield NO_RELEVANT_INFO_REPLY
        return

    settings = settings_factory()

    async for fragment in generation.generate_answer(
        question, chunks, model=settings.ollama_model, host=settings.ollama_host
    ):
        yield fragment
