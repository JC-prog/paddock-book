from src.core import embeddings as embeddings_module
from src.core.config import Settings
from src.modules.chat import generation as generation_module
from src.modules.chat import retrieval as retrieval_module


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
        bedrock_client = embeddings.get_bedrock_client(settings.aws_region)
        query_embedding = retrieval.embed_question(question, bedrock_client)
        return retrieval.retrieve_relevant_chunks(conn, department, query_embedding)
    finally:
        conn.close()


async def generate_reply(
    question: str,
    chunks: list[dict],
    *,
    settings_factory=Settings,
    generation=generation_module,
):
    settings = settings_factory()

    async for fragment in generation.generate_answer(
        question, chunks, model=settings.ollama_model, host=settings.ollama_host
    ):
        yield fragment
