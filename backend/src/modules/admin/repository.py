import psycopg

CHAT_PROVIDER_SETTINGS_COLUMNS = (
    "active_provider",
    "ollama_model_override",
    "bedrock_model",
    "openai_compatible_base_url",
    "openai_compatible_api_key",
    "openai_compatible_model",
    "updated_at",
)


def get_log_destination_setting(conn: psycopg.Connection) -> bool | None:
    with conn.cursor() as cur:
        cur.execute("SELECT log_to_file FROM app_settings WHERE id = 1")
        row = cur.fetchone()

    return row[0] if row else None


def set_log_destination_setting(conn: psycopg.Connection, value: bool) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO app_settings (id, log_to_file) VALUES (1, %s)
            ON CONFLICT (id) DO UPDATE SET log_to_file = EXCLUDED.log_to_file
            """,
            (value,),
        )


def promote_to_admin(conn: psycopg.Connection, email: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET is_admin = true WHERE email = %s RETURNING id, email",
            (email,),
        )
        row = cur.fetchone()

    return {"id": row[0], "email": row[1]} if row else None


def get_chat_provider_settings(conn: psycopg.Connection) -> dict | None:
    columns = CHAT_PROVIDER_SETTINGS_COLUMNS
    with conn.cursor() as cur:
        cur.execute(f"SELECT {', '.join(columns)} FROM chat_provider_settings WHERE id = 1")
        row = cur.fetchone()

    return dict(zip(columns, row)) if row else None


def upsert_chat_provider_settings(conn: psycopg.Connection, updates: dict) -> None:
    """Partial update (research.md): only columns present in `updates` are
    changed. On first call (no row yet), any column left out of `updates`
    gets the table's own DEFAULT rather than being included in the INSERT."""
    settable_columns = set(CHAT_PROVIDER_SETTINGS_COLUMNS) - {"updated_at"}
    keys = [key for key in updates if key in settable_columns]

    columns = ["id", *keys]
    values = [1, *(updates[key] for key in keys)]
    placeholders = ", ".join(["%s"] * len(columns))
    set_clauses = ", ".join([f"{key} = EXCLUDED.{key}" for key in keys] + ["updated_at = now()"])

    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO chat_provider_settings ({", ".join(columns)})
            VALUES ({placeholders})
            ON CONFLICT (id) DO UPDATE SET {set_clauses}
            """,
            values,
        )
