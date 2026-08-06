import psycopg

from src.core.config import Settings


def get_connection() -> psycopg.Connection:
    settings = Settings()
    return psycopg.connect(settings.database_url)
