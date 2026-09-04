"""
Rollback the product-intel DB migration.

Drops the view, restores the original table from the legacy copy,
drops the normalised tables.  events/snapshots/knowledge_base are NOT
recreated — they were confirmed empty before deletion, nothing to restore.

Usage:
    python -m scripts.rollback_db          # uses NEON_URL from env
    python -m scripts.rollback_db --url <DATABASE_URL>
"""

import argparse
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()


def run_rollback(engine) -> None:
    """Reverse the migration inside one transaction."""
    with engine.begin() as conn:
        conn.execute(text("DROP VIEW IF EXISTS product_performance"))
        conn.execute(text("ALTER TABLE product_performance_legacy RENAME TO product_performance"))
        conn.execute(text("DROP TABLE IF EXISTS product_metrics_daily"))
        conn.execute(text("DROP TABLE IF EXISTS products"))
        # events/snapshots/knowledge_base are not recreated —
        # they were empty, nothing to restore.

    print("✓ Rollback completed. 'product_performance' table restored from legacy copy.")


def main():
    parser = argparse.ArgumentParser(description="Rollback the product-intel DB migration.")
    parser.add_argument("--url", default=None, help="Database URL (overrides NEON_URL env var)")
    args = parser.parse_args()

    db_url = args.url or os.getenv("NEON_URL")
    if not db_url:
        print("Error: no database URL. Set NEON_URL or pass --url.", file=sys.stderr)
        sys.exit(1)

    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    engine = create_engine(db_url)
    run_rollback(engine)


if __name__ == "__main__":
    main()
