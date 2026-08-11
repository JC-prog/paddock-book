import asyncio
from datetime import datetime, timezone
from pathlib import Path

from src.core.config import Settings
from src.core.db import get_connection
from src.modules.chat import service as chat_service_module
from src.modules.chat.retrieval import RETRIEVAL_LIMIT
from src.modules.eval import judge as judge_module
from src.modules.eval import question_gen as question_gen_module
from src.modules.eval import repository as repository_module
from src.modules.eval.question_gen import QuestionGenerationError
from src.modules.eval.schemas import EvalQuestion, EvalReport, EvalResult, EvalSet


class NoIngestedContentError(Exception):
    pass


class EvalSetNotFoundError(Exception):
    pass


def _sample_chunks(chunks: list[str], count: int) -> list[str]:
    if len(chunks) <= count:
        return chunks
    step = len(chunks) / count
    indices = [int(i * step) for i in range(count)]
    return [chunks[i] for i in indices]


def generate_eval_set(
    department: str,
    *,
    questions_per_document: int = 3,
    conn,
    repository=repository_module,
    question_gen=question_gen_module,
    settings_factory=Settings,
) -> Path:
    documents = repository.list_documents_with_chunks(conn, department)
    if not documents:
        raise NoIngestedContentError(f"no ingested documents found for department {department!r}")

    settings = settings_factory()
    questions: list[EvalQuestion] = []
    for title, chunks in documents.items():
        for chunk_text in _sample_chunks(chunks, questions_per_document):
            try:
                question, expected_answer = question_gen.generate_question(
                    chunk_text, model=settings.ollama_model, host=settings.ollama_host
                )
            except QuestionGenerationError:
                continue
            questions.append(
                EvalQuestion(
                    question=question, expected_answer=expected_answer, source_document_title=title
                )
            )

    eval_set = EvalSet(
        department=department,
        generated_at=datetime.now(timezone.utc),
        questions_per_document=questions_per_document,
        questions=questions,
    )
    return eval_set.save()


def _find_rank(chunks: list[dict], source_document_title: str) -> int | None:
    for i, chunk in enumerate(chunks, start=1):
        if chunk["document_title"] == source_document_title:
            return i
    return None


async def _consume(async_gen) -> str:
    fragments = []
    async for fragment in async_gen:
        fragments.append(fragment)
    return "".join(fragments)


def run_eval(
    eval_set_path,
    *,
    connection_factory=get_connection,
    chat_service=chat_service_module,
    judge=judge_module,
    settings_factory=Settings,
) -> Path:
    path = Path(eval_set_path)
    if not path.exists():
        raise EvalSetNotFoundError(f"eval set not found: {eval_set_path}")

    eval_set = EvalSet.load(path)
    settings = settings_factory()

    results: list[EvalResult] = []
    hit_count = 0
    reciprocal_ranks: list[float] = []
    correct_count = 0
    judged_count = 0

    for q in eval_set.questions:
        conn = connection_factory()
        try:
            chunks = chat_service.retrieve_context(
                q.question, eval_set.department, conn=conn, settings_factory=settings_factory
            )
        except Exception as exc:
            results.append(
                EvalResult(
                    question=q.question,
                    source_document_title=q.source_document_title,
                    retrieved=False,
                    rank=None,
                    generated_answer=None,
                    judged_correct=None,
                    failure_reason=f"retrieval: {exc}",
                )
            )
            reciprocal_ranks.append(0.0)
            continue

        rank = _find_rank(chunks, q.source_document_title)
        retrieved = rank is not None
        if retrieved:
            hit_count += 1
        reciprocal_ranks.append(1 / rank if rank else 0.0)

        try:
            generated_answer = asyncio.run(
                _consume(chat_service.generate_reply(q.question, chunks, settings_factory=settings_factory))
            )
        except Exception as exc:
            results.append(
                EvalResult(
                    question=q.question,
                    source_document_title=q.source_document_title,
                    retrieved=retrieved,
                    rank=rank,
                    generated_answer=None,
                    judged_correct=None,
                    failure_reason=f"generation: {exc}",
                )
            )
            continue

        try:
            correct = judge.judge_answer(
                q.expected_answer, generated_answer, model=settings.ollama_model, host=settings.ollama_host
            )
        except Exception as exc:
            results.append(
                EvalResult(
                    question=q.question,
                    source_document_title=q.source_document_title,
                    retrieved=retrieved,
                    rank=rank,
                    generated_answer=generated_answer,
                    judged_correct=None,
                    failure_reason=f"judging: {exc}",
                )
            )
            continue

        judged_count += 1
        if correct:
            correct_count += 1
        results.append(
            EvalResult(
                question=q.question,
                source_document_title=q.source_document_title,
                retrieved=retrieved,
                rank=rank,
                generated_answer=generated_answer,
                judged_correct=correct,
                failure_reason=None,
            )
        )

    total = len(eval_set.questions)
    hit_rate = hit_count / total if total else 0.0
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0
    answer_accuracy = correct_count / judged_count if judged_count else 0.0

    report = EvalReport(
        eval_set_path=str(eval_set_path),
        run_at=datetime.now(timezone.utc),
        k=RETRIEVAL_LIMIT,
        results=results,
        hit_rate=hit_rate,
        mrr=mrr,
        answer_accuracy=answer_accuracy,
        judged_count=judged_count,
    )
    return report.save()
