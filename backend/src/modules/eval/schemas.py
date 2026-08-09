from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

EVAL_SETS_DIR = Path("data/eval/sets")
EVAL_REPORTS_DIR = Path("data/eval/reports")

_TIMESTAMP_FORMAT = "%Y%m%d-%H%M%S-%f"


def _escape_cell(text: str) -> str:
    # Model-generated text can contain newlines or literal "|" characters,
    # either of which would silently corrupt the markdown table's structure.
    return text.replace("|", "\\|").replace("\n", " ").strip()


class EvalQuestion(BaseModel):
    question: str
    expected_answer: str
    source_document_title: str


class EvalSet(BaseModel):
    department: str
    generated_at: datetime
    questions_per_document: int
    questions: list[EvalQuestion]

    def save(self, *, base_dir: Path = EVAL_SETS_DIR) -> Path:
        base_dir = Path(base_dir)
        base_dir.mkdir(parents=True, exist_ok=True)
        # Uses the actual save-time clock, not self.generated_at, so two
        # saves of eval sets built in the same wall-clock second (as can
        # happen in a fast test, or a script calling generate_eval_set()
        # twice quickly) never collide on the same filename (FR-004).
        timestamp = datetime.now().strftime(_TIMESTAMP_FORMAT)
        path = base_dir / f"{self.department}-{timestamp}.json"
        path.write_text(self.model_dump_json(indent=2))
        return path

    @classmethod
    def load(cls, path: Path) -> "EvalSet":
        return cls.model_validate_json(Path(path).read_text())


class EvalResult(BaseModel):
    question: str
    source_document_title: str
    retrieved: bool
    rank: int | None
    generated_answer: str | None
    judged_correct: bool | None
    failure_reason: str | None


class EvalReport(BaseModel):
    eval_set_path: str
    run_at: datetime
    k: int
    results: list[EvalResult]
    hit_rate: float
    mrr: float
    answer_accuracy: float
    judged_count: int

    def to_markdown(self) -> str:
        lines = [
            "# Eval Report",
            "",
            f"**Eval set**: {self.eval_set_path}",
            f"**Run at**: {self.run_at.isoformat()}",
            f"**k**: {self.k}",
            "",
            "## Aggregate Metrics",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| Hit Rate@{self.k} | {self.hit_rate} |",
            f"| MRR | {self.mrr} |",
            f"| Answer accuracy | {self.answer_accuracy} ({self.judged_count}/{len(self.results)} judged) |",
            "",
            "## Per-Question Results",
            "",
            "| # | Question | Source Document | Retrieved | Rank | Generated Answer | Judged Correct | Failure |",
            "|---|---|---|---|---|---|---|---|",
        ]

        for i, result in enumerate(self.results, start=1):
            retrieved_cell = "✅" if result.retrieved else "❌"
            rank_cell = str(result.rank) if result.rank is not None else "—"
            answer_cell = _escape_cell(result.generated_answer) if result.generated_answer else "—"
            if result.judged_correct is True:
                judged_cell = "✅"
            elif result.judged_correct is False:
                judged_cell = "❌"
            else:
                judged_cell = "—"
            failure_cell = _escape_cell(result.failure_reason) if result.failure_reason else ""
            lines.append(
                f"| {i} | {_escape_cell(result.question)} | {_escape_cell(result.source_document_title)} | "
                f"{retrieved_cell} | {rank_cell} | {answer_cell} | {judged_cell} | {failure_cell} |"
            )

        return "\n".join(lines) + "\n"

    def save(self, *, base_dir: Path = EVAL_REPORTS_DIR) -> Path:
        base_dir = Path(base_dir)
        base_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(self.eval_set_path).stem
        timestamp = datetime.now().strftime(_TIMESTAMP_FORMAT)
        path = base_dir / f"{stem}-{timestamp}.md"
        path.write_text(self.to_markdown())
        return path
