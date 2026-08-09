# Quickstart: Admin Logging Panel

## Prerequisites

- Postgres running with `db/init/003_admin_settings.sql` applied. If
  your local database already existed before this feature (i.e. you've
  used this repo before), the `docker-entrypoint-initdb.d` scripts won't
  re-run automatically — either:
  - `docker compose down -v && docker compose up -d` for a fresh volume, or
  - run the new file's statements manually against your existing database.
- Backend running from `backend/` (`uvicorn src.main:app --reload`).
- An existing account (register one per feature 007's quickstart if
  needed).

## Steps

1. **Promote an account to admin (FR-007, US2)**

   ```
   cd backend
   python -m src.modules.admin.cli --promote-admin you@example.com
   ```

   **Expected**: exit code `0`, a success message, and an
   `admin_granted` log line (per `data-model.md`) naming that email.

2. **Promoting an unknown email fails cleanly (FR-008)**

   ```
   python -m src.modules.admin.cli --promote-admin nobody@example.com
   ```

   **Expected**: exit code `1`, a clear error, no account created.

3. **Log in and confirm admin status is visible (data-model.md)**

   ```
   curl -s -X POST http://localhost:8000/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"you@example.com","password":"<your password>"}'
   ```

   **Expected**: the response's `user` object includes `"is_admin": true`.

4. **View the current setting (FR-002)**

   ```
   curl -s http://localhost:8000/v1/admin/settings/log-destination \
     -H "Authorization: Bearer <access_token from step 3>"
   ```

   **Expected**: `200 {"log_to_file": true}` (the default, per
   `contracts/admin-api.md`) — even though no row exists in
   `app_settings` yet.

5. **Change it and confirm the audit event (FR-003, FR-010)**

   ```
   curl -s -X PUT http://localhost:8000/v1/admin/settings/log-destination \
     -H "Authorization: Bearer <access_token>" \
     -H "Content-Type: application/json" \
     -d '{"log_to_file": false}'
   ```

   **Expected**: `200 {"log_to_file": false}`, and a
   `log_destination_changed` log line naming the admin account and the
   new value.

6. **A non-admin is rejected (FR-004, SC-002)**

   Log in as an account that hasn't been promoted, repeat step 4 with
   its token. **Expected**: `403 Forbidden`.

7. **The change takes effect on the next restart, not before (FR-006)**

   Restart the backend (`uvicorn ... --reload` triggers this
   automatically on a file save, or stop/start it manually). Trigger a
   request, then check `backend/logs/` (feature 011).

   **Expected**: with `log_to_file` now `false` from step 5, no new
   entries appear in `backend/logs/app.log` after the restart — logging
   is stdout-only, matching the DB-backed setting rather than whatever
   `backend/.env`'s `LOG_TO_FILE` says.

8. **Admin panel page (US1, frontend)**

   Log in as the admin account in the browser, navigate to the admin
   page. **Expected**: the current setting is displayed, changing it
   calls the API from steps 4–5, and a non-admin account never sees this
   page at all (route-guarded, per feature 007's existing guard pattern).

## Cleanup

Set `log_to_file` back to `true` via the panel or a `PUT` call if you
want feature 011's default local-file logging back for further local
development.
