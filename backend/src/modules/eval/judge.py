import json

import ollama

_PROMPT_TEMPLATE = (
    "You are grading an AI-generated answer for a RAG evaluation harness. "
    "Given the expected answer and the generated answer below, decide "
    "whether the generated answer is correct — conveys the same "
    "substance as the expected answer, even if worded differently. "
    'Reply with ONLY a JSON object of the form {{"correct": true}} or '
    '{{"correct": false}}, nothing else.\n\n'
    "Expected answer: {expected_answer}\n"
    "Generated answer: {generated_answer}"
)


class JudgingError(Exception):
    pass


def _default_client_factory(host: str):
    return ollama.Client(host=host)


def judge_answer(
    expected_answer: str,
    generated_answer: str,
    *,
    model: str,
    host: str,
    client_factory=_default_client_factory,
) -> bool:
    client = client_factory(host)
    prompt = _PROMPT_TEMPLATE.format(expected_answer=expected_answer, generated_answer=generated_answer)

    try:
        response = client.chat(model=model, messages=[{"role": "user", "content": prompt}])
        payload = json.loads(response["message"]["content"])
        correct = payload["correct"]
        if not isinstance(correct, bool):
            raise ValueError(f"'correct' was not a boolean: {correct!r}")
    except Exception as exc:
        raise JudgingError(f"could not judge the answer: {exc}") from exc

    return correct
