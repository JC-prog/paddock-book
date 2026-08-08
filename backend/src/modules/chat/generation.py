import ollama

NO_RELEVANT_INFO_REPLY = "I don't have relevant information to answer that question."

SYSTEM_PROMPT = (
    "You are a regulation assistant for F1 team staff. Answer the "
    "question using only the following regulation excerpts. If the "
    "excerpts don't actually answer the question, respond with exactly: "
    f'"{NO_RELEVANT_INFO_REPLY}" rather than guessing or using general '
    "knowledge."
)


def _default_client_factory(host: str):
    return ollama.AsyncClient(host=host)


def _build_messages(question: str, chunks: list[dict]) -> list[dict]:
    context = "\n\n".join(
        f"[{chunk['document_title']}] {chunk['chunk_text']}" for chunk in chunks
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Regulation excerpts:\n{context}\n\nQuestion: {question}",
        },
    ]


async def generate_answer(
    question: str,
    chunks: list[dict],
    *,
    model: str,
    host: str,
    client_factory=_default_client_factory,
):
    client = client_factory(host)
    messages = _build_messages(question, chunks)

    async for part in await client.chat(model=model, messages=messages, stream=True):
        content = part["message"]["content"]
        if content:
            yield content
