-- Admin logging panel schema. Runs automatically on first container
-- startup via /docker-entrypoint-initdb.d/ for a brand-new volume; on an
-- already-initialized database, apply by hand (see
-- specs/012-admin-logging-panel/quickstart.md Prerequisites). See
-- specs/012-admin-logging-panel/data-model.md for the design this
-- implements.

ALTER TABLE users ADD COLUMN is_admin boolean NOT NULL DEFAULT false;

-- Deliberately a single-row table, not a general key-value settings
-- store (see research.md) — id is always 1.
CREATE TABLE app_settings (
    id smallint PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    log_to_file boolean NOT NULL DEFAULT true
);
