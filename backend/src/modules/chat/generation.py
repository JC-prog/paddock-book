import asyncio
from dataclasses import dataclass

import boto3
import ollama
from openai import AsyncOpenAI

NO_RELEVANT_INFO_REPLY = "I don't have relevant information to answer that question."

SYSTEM_PROMPT = (
    "You are a regulation assistant for F1 team staff. Answer the "
    "question using only the following regulation excerpts. If the "
    "excerpts don't actually answer the question, respond with exactly: "
    f'"{NO_RELEVANT_INFO_REPLY}" rather than guessing or using general '
    "knowledge."
)


@dataclass
class ChatProviderConfig:
    """Fully-resolved chat-generation provider configuration — see
    data-model.md's "Read shape consumed by chat/generation.py". Built by
    chat/service.py; this module has no DB/Settings dependency of its
    own (Constitution Principle V)."""

    provider: str  # "ollama" | "bedrock" | "openai_compatible"
    ollama_model: str
    ollama_host: str
    bedrock_model: str | None = None
    aws_region: str = "us-east-1"
    openai_compatible_base_url: str | None = None
    openai_compatible_api_key: str | None = None
    openai_compatible_model: str | None = None


def _default_ollama_client_factory(host: str):
    return ollama.AsyncClient(host=host)


def _default_bedrock_client_factory(region_name: str):
    # Matches core/embeddings.py::get_bedrock_client's existing
    # construction (this is the project's first Bedrock *chat* usage,
    # embeddings already used a sync boto3 client this same way).
    return boto3.client("bedrock-runtime", region_name=region_name)


def _default_openai_client_factory(base_url: str, api_key: str):
    return AsyncOpenAI(base_url=base_url, api_key=api_key)


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


async def _generate_ollama(messages: list[dict], provider_config: ChatProviderConfig, client_factory):
    client = client_factory(provider_config.ollama_host)

    async for part in await client.chat(
        model=provider_config.ollama_model, messages=messages, stream=True
    ):
        content = part["message"]["content"]
        if content:
            yield content


async def _generate_bedrock(messages: list[dict], provider_config: ChatProviderConfig, client_factory):
    """Streams via the Bedrock Converse API — AWS's unified interface
    across model providers, needed since an admin can enter any Bedrock
    model identifier (research.md). boto3 has no async client, so the
    blocking `converse_stream` iteration runs in a background thread,
    pushing decoded text deltas onto a queue the async generator
    consumes — the bridge research.md settled on over adding a whole
    separate async-AWS-SDK dependency."""
    client = client_factory(provider_config.aws_region)
    system_blocks = [{"text": m["content"]} for m in messages if m["role"] == "system"]
    converse_messages = [
        {"role": m["role"], "content": [{"text": m["content"]}]}
        for m in messages
        if m["role"] != "system"
    ]

    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    done = object()

    def _consume_stream() -> None:
        try:
            response = client.converse_stream(
                modelId=provider_config.bedrock_model,
                messages=converse_messages,
                system=system_blocks,
            )
            for event in response["stream"]:
                text = event.get("contentBlockDelta", {}).get("delta", {}).get("text")
                if text:
                    loop.call_soon_threadsafe(queue.put_nowait, text)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, done)

    asyncio.ensure_future(asyncio.to_thread(_consume_stream))

    while True:
        item = await queue.get()
        if item is done:
            break
        yield item


async def _generate_openai_compatible(
    messages: list[dict], provider_config: ChatProviderConfig, client_factory
):
    """Uses the official openai SDK's async client purely as an HTTP
    client against an admin-supplied base_url — covers OpenAI itself and
    any other OpenAI-API-compatible service through one integration
    (research.md). Already streams natively via async iteration, unlike
    Bedrock, so no thread bridge is needed here."""
    client = client_factory(
        provider_config.openai_compatible_base_url, provider_config.openai_compatible_api_key
    )
    stream = await client.chat.completions.create(
        model=provider_config.openai_compatible_model, messages=messages, stream=True
    )

    async for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content


async def generate_answer(
    question: str,
    chunks: list[dict],
    *,
    provider_config: ChatProviderConfig,
    ollama_client_factory=_default_ollama_client_factory,
    bedrock_client_factory=_default_bedrock_client_factory,
    openai_client_factory=_default_openai_client_factory,
):
    messages = _build_messages(question, chunks)

    if provider_config.provider == "ollama":
        async for fragment in _generate_ollama(messages, provider_config, ollama_client_factory):
            yield fragment
        return

    if provider_config.provider == "bedrock":
        async for fragment in _generate_bedrock(messages, provider_config, bedrock_client_factory):
            yield fragment
        return

    if provider_config.provider == "openai_compatible":
        async for fragment in _generate_openai_compatible(messages, provider_config, openai_client_factory):
            yield fragment
        return

    raise NotImplementedError(f"no chat generation branch yet for provider {provider_config.provider!r}")
