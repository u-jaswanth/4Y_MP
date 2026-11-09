"""
Idempotent helper that makes sure the `vector` Postgres extension
(from pgvector) is installed before we touch any of the vector_*
tables.

This is called once at API startup (see app/main.py) and from the
standalone CLI script, so a fresh database "just works" the first
time as long as the DB user has permission to create extensions
(true for the default local `postgres` superuser used in
.env.example). If the DB user lacks that permission, an admin only
needs to run this once, manually:

    CREATE EXTENSION IF NOT EXISTS vector;
"""

from sqlalchemy import text

from app.database import engine


def ensure_pgvector_extension() -> None:
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    except Exception as error:  # noqa: BLE001
        # Non-fatal: if the DB user can't create extensions, we just
        # log it - auth/report endpoints don't need pgvector, only
        # report analysis and the AI chat do. An admin can run the
        # CREATE EXTENSION statement above manually.
        print(
            "[pgvector] Could not ensure the 'vector' extension exists "
            f"automatically ({error}). If report analysis / chat later "
            "fail with a Postgres error, run this once as a DB admin: "
            "CREATE EXTENSION IF NOT EXISTS vector;"
        )
