import json

import boto3
import ollama

EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
EMBEDDING_DIMENSIONS = 1024


def get_bedrock_client(region_name: str):
    return boto3.client("bedrock-runtime", region_name=region_name)


def embed_text(text: str, client) -> list[float]:
    try:
        response = client.invoke_model(
            modelId=EMBEDDING_MODEL_ID,
            body=json.dumps({"inputText": text, "dimensions": EMBEDDING_DIMENSIONS}),
        )
        payload = json.loads(response["body"].read())
    except Exception as exc:
        raise RuntimeError(f"Bedrock embedding call failed: {exc}") from exc

    return payload["embedding"]


def embed_text_ollama(text: str, *, host: str, model: str) -> list[float]:
    """Local-dev stand-in for embed_text. Produces vectors in a different
    space than Titan V2 (different model), so ingestion and retrieval must
    both use the same provider consistently — never mix the two."""
    try:
        response = ollama.Client(host=host).embed(model=model, input=text)
    except Exception as exc:
        raise RuntimeError(f"Ollama embedding call failed: {exc}") from exc

    return list(response.embeddings[0])


def embed(
    text: str,
    *,
    provider: str,
    region_name: str,
    ollama_host: str,
    ollama_model: str,
) -> list[float]:
    """Provider dispatch so ingestion and chat retrieval don't each
    duplicate the bedrock-vs-ollama branch."""
    if provider == "ollama":
        return embed_text_ollama(text, host=ollama_host, model=ollama_model)
    return embed_text(text, get_bedrock_client(region_name))
