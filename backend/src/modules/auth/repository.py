from datetime import datetime

import psycopg


def create_user(conn: psycopg.Connection, email: str, password_hash: str, department: str) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (email, password_hash, department)
            VALUES (%s, %s, %s)
            RETURNING id, email, department, created_at
            """,
            (email, password_hash, department),
        )
        row = cur.fetchone()

    return {"id": row[0], "email": row[1], "department": row[2], "created_at": row[3]}


def get_user_by_email(conn: psycopg.Connection, email: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, email, password_hash, department FROM users WHERE email = %s",
            (email,),
        )
        row = cur.fetchone()

    if row is None:
        return None

    return {"id": row[0], "email": row[1], "password_hash": row[2], "department": row[3]}


def get_user_by_id(conn: psycopg.Connection, user_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, email, department FROM users WHERE id = %s",
            (user_id,),
        )
        row = cur.fetchone()

    if row is None:
        return None

    return {"id": row[0], "email": row[1], "department": row[2]}


def create_refresh_token(
    conn: psycopg.Connection, user_id: str, token_hash: str, expires_at: datetime
) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
            VALUES (%s, %s, %s)
            RETURNING id, user_id, expires_at
            """,
            (user_id, token_hash, expires_at),
        )
        row = cur.fetchone()

    return {"id": row[0], "user_id": row[1], "expires_at": row[2]}


def get_valid_refresh_token(conn: psycopg.Connection, token_hash: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, expires_at
            FROM refresh_tokens
            WHERE token_hash = %s AND revoked_at IS NULL AND expires_at > now()
            """,
            (token_hash,),
        )
        row = cur.fetchone()

    if row is None:
        return None

    return {"id": row[0], "user_id": row[1], "expires_at": row[2]}


def revoke_refresh_token(conn: psycopg.Connection, token_hash: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE refresh_tokens SET revoked_at = now() WHERE token_hash = %s",
            (token_hash,),
        )
