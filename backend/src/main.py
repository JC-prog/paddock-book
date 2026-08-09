from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.db import get_connection
from src.core.logging import configure_logging


def _read_log_destination_from_db() -> bool | None:
    # Deliberately not importing modules/admin/repository.py here — core/
    # must not depend on modules/, per the constitution's separation of
    # concerns principle (see research.md). This tiny query is a justified,
    # intentional duplication of that repository's SELECT.
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT log_to_file FROM app_settings WHERE id = 1")
            row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


configure_logging(db_log_to_file_factory=_read_log_destination_from_db)

# Deliberately imported only after configure_logging() has run: some of
# these modules do real work at import time (e.g. core/celery_app.py
# constructs the Celery app, with its own graceful-degradation warning
# on a bad Settings() read) that must go through the JSON logging
# pipeline like everything else, not fall back to Python's unformatted
# last-resort handler because it ran before the JSON formatter was
# attached.
from src.core.middleware import RequestLoggingMiddleware  # noqa: E402
from src.modules.admin.router import router as admin_router  # noqa: E402
from src.modules.auth.router import router as auth_router  # noqa: E402
from src.modules.chat.router import router as chat_router  # noqa: E402
from src.modules.health.router import router as health_router  # noqa: E402
from src.modules.jobs.router import router as jobs_router  # noqa: E402

app = FastAPI(title="PaddockBook API")

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.add_middleware(RequestLoggingMiddleware)

# Routers
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(jobs_router)
