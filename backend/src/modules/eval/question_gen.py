import json

import ollama

_PROMPT_TEMPLATE = (
    "You are generating a test question for a RAG evaluation harness. "
    "Given the following regulation excerpt, write ONE question that is "
    "answerable using ONLY this excerpt, plus a short expected answer. "
    'Reply with ONLY a JSON object of the form {{"question": "...", '
    '"expected_answer": "..."}}, nothing else.\n\n'
    "Excerpt:\n{chunk_text}"
)


class QuestionGenerationError(Exception):
    pass


def _default_client_factory(host: str):
    return ollama.Client(host=host)


def generate_question(
    chunk_text: str, *, model: str, host: str, client_factory=_default_client_factory
) -> tuple[str, str]:
    client = client_factory(host)
    prompt = _PROMPT_TEMPLATE.format(chunk_text=chunk_text)

    try:
        response = client.chat(model=model, messages=[{"role": "user", "content": prompt}])
        payload = json.loads(response["message"]["content"])
        question = payload["question"]
        expected_answer = payload["expected_answer"]
    except Exception as exc:
        raise QuestionGenerationError(f"could not generate a question: {exc}") from exc

    return question, expected_answer
