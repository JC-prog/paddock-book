import psycopg

from src.core import embeddings as embeddings_module
from src.core.config import Settings
from src.modules.admin import repository as admin_repository_module
from src.modules.chat import generation as generation_module
from src.modules.chat import retrieval as retrieval_module
from src.modules.chat.generation import NO_RELEVANT_INFO_REPLY, ChatProviderConfig


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


def resolve_provider_config(
    *,
    conn,
    admin_repository=admin_repository_module,
    settings_factory=Settings,
) -> ChatProviderConfig:
    """Builds the fully-resolved provider config chat generation actually
    uses, reading admin.repository directly rather than through
    admin/service.py's mutation-validation layer — mirrors the existing
    cross-module read precedent in modules/jobs/service.py (research.md)."""
    settings = settings_factory()
    row = admin_repository.get_chat_provider_settings(conn)

    if row is None:
        return ChatProviderConfig(
            provider="ollama",
            ollama_model=settings.ollama_model,
            ollama_host=settings.ollama_host,
            aws_region=settings.aws_region,
        )

    return ChatProviderConfig(
        provider=row["active_provider"],
        ollama_model=row["ollama_model_override"] or settings.ollama_model,
        ollama_host=settings.ollama_host,
        bedrock_model=row["bedrock_model"],
        aws_region=settings.aws_region,
        openai_compatible_base_url=row["openai_compatible_base_url"],
        openai_compatible_api_key=row["openai_compatible_api_key"],
        openai_compatible_model=row["openai_compatible_model"],
    )


async def generate_reply(
    question: str,
    chunks: list[dict],
    *,
    provider_config: ChatProviderConfig,
    generation=generation_module,
):
    if not chunks:
        # Deterministic short-circuit (FR-005) — the requester's department
        # has no ingested content at all, so there's nothing to guess from;
        # skip the LLM call entirely rather than relying on it to refuse.
        yield NO_RELEVANT_INFO_REPLY
        return

    async for fragment in generation.generate_answer(question, chunks, provider_config=provider_config):
        yield fragment
