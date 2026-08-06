-- Local authentication schema. Runs automatically on first container
-- startup via /docker-entrypoint-initdb.d/ for a brand-new volume; on an
-- already-initialized database, apply by hand (see
-- specs/007-user-authentication/quickstart.md step 1). See
-- specs/007-user-authentication/data-model.md for the design this
-- implements. Reuses the `department` enum defined in 001_init_schema.sql.

CREATE TABLE users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email text NOT NULL UNIQUE,
    password_hash text NOT NULL,
    department department NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE refresh_tokens (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    token_hash text NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz
);
