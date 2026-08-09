import psycopg


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
