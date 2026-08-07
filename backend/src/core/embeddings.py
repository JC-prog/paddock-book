import json

import boto3

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
