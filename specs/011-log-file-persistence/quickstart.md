# Quickstart: Log File Persistence

## Prerequisites

- Backend running locally from `backend/` (`uvicorn src.main:app --reload`)
  — the default `logs/app.log` path resolves relative to this working
  directory.

## Steps

1. **A real file appears (FR-001, US1)**

   Start the backend (file persistence defaults on — no config needed),
   then:

   ```
   curl -s http://localhost:8000/health
   cat backend/logs/app.log
   ```

   **Expected**: the file exists and its last line is the same JSON
   request-log entry that also appeared on stdout for that request.

2. **Logs survive the process (SC-002)**

   Stop the backend process entirely, then:

   ```
   cat backend/logs/app.log
   ```

   **Expected**: the file's contents are unchanged and still fully
   readable — nothing about them depended on the process still running.

3. **Toggle it off (FR-002)**

   Set `LOG_TO_FILE=false` in `backend/.env`, restart the backend, delete
   `backend/logs/` first if it exists, then repeat step 1.

   **Expected**: no `backend/logs/` directory is created at all — logging
   continues normally on stdout only.

4. **Rotation caps disk usage (FR-003, FR-004, US2)**

   With file persistence back on (`LOG_TO_FILE=true` or unset), generate
   enough log volume to exceed `log_file_max_bytes` (default 10 MB) — for
   example, loop a few thousand `curl http://localhost:8000/health`
   requests, or temporarily lower `LOG_FILE_MAX_BYTES` in `.env` to
   something small (e.g. `2048`) to trigger rollover quickly without
   needing real volume.

   **Expected**: `backend/logs/` contains `app.log` plus numbered backups
   (`app.log.1`, `app.log.2`, …), never more than
   `log_file_backup_count + 1` files total, and total directory size
   stays within `log_file_max_bytes * (log_file_backup_count + 1)`
   throughout — confirm with `ls -la backend/logs/` and `du -sh backend/logs/`.

5. **A broken destination doesn't break the app (FR-005)**

   Set `LOG_FILE_PATH` to somewhere the process can't write (e.g. a path
   under `/root/` if not running as root), restart the backend.

   **Expected**: the backend still starts and serves `GET /health`
   normally — check stdout for a `WARNING`-level line noting the file
   handler couldn't be set up, and confirm no log file was created at
   that broken path.

## Cleanup

`backend/logs/` is gitignored — delete it locally when done; nothing
here needs to be committed.
