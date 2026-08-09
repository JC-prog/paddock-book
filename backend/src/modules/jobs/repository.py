import json

import psycopg


class DuplicateJobError(Exception):
    pass


def _row_to_job(row: tuple) -> dict:
    (
        id_,
        job_type,
        target,
        status,
        params,
        result,
        error,
        triggered_by_email,
        created_at,
        started_at,
        finished_at,
    ) = row
    return {
        "id": str(id_),
        "job_type": job_type,
        "target": target,
        "status": status,
        "params": params,
        "result": result,
        "error": error,
        "triggered_by_email": triggered_by_email,
        "created_at": created_at,
        "started_at": started_at,
        "finished_at": finished_at,
    }


_SELECT_COLUMNS = (
    "id, job_type, target, status, params, result, error, "
    "triggered_by_email, created_at, started_at, finished_at"
)


def insert_job(
    conn: psycopg.Connection, *, job_type: str, target: str, params: dict, triggered_by_email: str
) -> dict:
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO job_runs (job_type, target, params, triggered_by_email)
                VALUES (%s, %s, %s, %s)
                RETURNING {_SELECT_COLUMNS}
                """,
                (job_type, target, json.dumps(params), triggered_by_email),
            )
            row = cur.fetchone()
    except psycopg.errors.UniqueViolation as exc:
        raise DuplicateJobError(
            f"a {job_type} job for target {target!r} is already queued or running"
        ) from exc

    return _row_to_job(row)


def mark_running(conn: psycopg.Connection, job_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE job_runs SET status = 'running', started_at = now() WHERE id = %s",
            (job_id,),
        )


def mark_finished(
    conn: psycopg.Connection,
    job_id: str,
    *,
    status: str,
    result: dict | None = None,
    error: str | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE job_runs
            SET status = %s, result = %s, error = %s, finished_at = now()
            WHERE id = %s
            """,
            (status, json.dumps(result) if result is not None else None, error, job_id),
        )


def list_jobs(conn: psycopg.Connection) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(f"SELECT {_SELECT_COLUMNS} FROM job_runs ORDER BY seq DESC")
        rows = cur.fetchall()

    return [_row_to_job(row) for row in rows]
