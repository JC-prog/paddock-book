import json
from dataclasses import dataclass

import boto3

from src.modules.ingestion.chunker import Chunk

EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
EMBEDDING_DIMENSIONS = 1024


@dataclass
class EmbeddedChunk:
    text: str
    order: int
    embedding: list[float]


def get_bedrock_client(region_name: str):
    return boto3.client("bedrock-runtime", region_name=region_name)


def embed_chunk(chunk: Chunk, client) -> EmbeddedChunk:
    try:
        response = client.invoke_model(
            modelId=EMBEDDING_MODEL_ID,
            body=json.dumps(
                {"inputText": chunk.text, "dimensions": EMBEDDING_DIMENSIONS}
            ),
        )
        payload = json.loads(response["body"].read())
    except Exception as exc:
        raise RuntimeError(f"Bedrock embedding call failed: {exc}") from exc

    return EmbeddedChunk(text=chunk.text, order=chunk.order, embedding=payload["embedding"])
