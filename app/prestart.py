from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

logger = logging.getLogger("prestart")

DEFAULT_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/banking"
DEFAULT_MAX_RETRIES = 30
DEFAULT_RETRY_DELAY_SECONDS = 2.0


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_max_retries() -> int:
    return int(os.getenv("DB_CONNECT_MAX_RETRIES", str(DEFAULT_MAX_RETRIES)))


def get_retry_delay_seconds() -> float:
    return float(os.getenv("DB_CONNECT_RETRY_DELAY", str(DEFAULT_RETRY_DELAY_SECONDS)))


async def wait_for_database(database_url: str, max_retries: int, retry_delay_seconds: float) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        for attempt in range(1, max_retries + 1):
            try:
                async with engine.connect() as connection:
                    await connection.execute(text("SELECT 1"))
                logger.info("Database connection established.")
                return
            except Exception as exc:
                if attempt == max_retries:
                    raise RuntimeError(
                        f"Database did not become available after {max_retries} attempts."
                    ) from exc

                logger.warning(
                    "Database unavailable on attempt %s/%s: %s",
                    attempt,
                    max_retries,
                    exc,
                )
                await asyncio.sleep(retry_delay_seconds)
    finally:
        await engine.dispose()


def run_migrations() -> None:
    project_root = Path(__file__).resolve().parent.parent
    alembic_config = Config(str(project_root / "alembic.ini"))
    logger.info("Running Alembic migrations.")
    command.upgrade(alembic_config, "head")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    database_url = get_database_url()
    max_retries = get_max_retries()
    retry_delay_seconds = get_retry_delay_seconds()

    logger.info(
        "Waiting for database before migrations (max_retries=%s, retry_delay=%ss).",
        max_retries,
        retry_delay_seconds,
    )
    try:
        asyncio.run(wait_for_database(database_url, max_retries, retry_delay_seconds))
        run_migrations()
    except Exception as exc:
        logger.error("Prestart failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
