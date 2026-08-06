# Contract: Ingestion CLI

This feature exposes no HTTP API — its interface is a command-line
invocation. This is the contract a developer (or a future automation)
depends on.

## Invocation

```bash
python -m src.modules.ingestion.cli \
  --file /path/to/regulation.pdf \
  --title "2026 Sporting Regulations" \
  --department sporting
```

| Flag | Required | Values | Description |
|---|---|---|---|
| `--file` | yes | any readable file path | The PDF to ingest |
| `--title` | yes | any non-empty string | Document title — also its identity for duplicate detection |
| `--department` | yes | `sporting` \| `technical` \| `financial` | Matches feature 005's `department` enum exactly |

## Outcomes

| Condition | Exit code | Database effect |
|---|---|---|
| Success | `0` | One new `documents` row, N new `document_chunks` rows, committed together |
| `--file` doesn't exist / isn't readable | non-zero | None — rejected before any parsing |
| `--department` isn't one of the three values | non-zero | None — rejected before any parsing |
| A `documents` row with the same `--title` already exists | non-zero | None — rejected before any parsing or embedding calls (research.md) |
| PDF has no extractable text, or is corrupted | non-zero | None |
| An embedding call fails partway through | non-zero | None — no partial data (FR-008) |

## Contract guarantees

- The database is **never** left in a partial state — every non-zero exit
  means zero rows were written for that run.
- A duplicate-title rejection happens **before** any Bedrock embedding
  calls are made, so a mistaken re-run never incurs embedding cost.
- Every written `document_chunks` row's `chunk_order` reflects the order
  chunks appeared in the source PDF, starting at 0.

## Changing this contract

Any change to the CLI's flags, exit-code meanings, or write guarantees is a
contract change: this file and `backend/tests/unit/test_ingestion_service.py`
/ `backend/tests/integration/test_ingestion_repository.py` MUST be updated
together (Constitution Principle III).
