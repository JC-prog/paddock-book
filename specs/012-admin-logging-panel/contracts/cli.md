# Contract: Admin Promotion CLI

## Invocation

```
python -m src.modules.admin.cli --promote-admin <email>
```

The only supported action — mirrors `modules/ingestion/cli.py`'s
argparse style.

## Behavior

1. Looks up the account by `<email>`.
2. If no matching account exists, prints a clear error to stderr and
   exits non-zero — no account is created (FR-008).
3. If a matching account exists, sets `is_admin = true` (idempotent — an
   already-admin account is left as-is, still exits `0`).
4. On a successful promotion (new or already-admin), records an
   `admin_granted` event (see `data-model.md`) and prints a success
   message to stdout.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Account now has admin access (whether newly granted or already had it). |
| `1` | No account matches the given email; nothing was changed. |

## Non-goals

- No in-app, self-service, or UI path grants admin access — this CLI,
  run by an operator with direct access to the backend, is the only way
  (FR-009).
- Does not create accounts — only promotes an existing one (FR-008).
