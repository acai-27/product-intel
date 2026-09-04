"""
Daily ingest pipeline — dialect-gated two-step upsert.

Registers new products first (ON CONFLICT DO NOTHING), then upserts
daily metrics (ON CONFLICT DO UPDATE).  Uses the matching SQLAlchemy
dialect insert so the exact same code path runs in both SQLite tests
and Postgres production.
"""

import pandas as pd
from sqlalchemy import Engine

from src.core.models import Product, ProductMetricsDaily


def _get_dialect_insert(engine: Engine):
    """Return the dialect-specific ``insert`` function."""
    dialect = engine.dialect.name
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    elif dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert
    else:
        raise NotImplementedError(f"No upsert support wired for dialect: {dialect}")
    return insert


def upsert_daily_metrics(df: pd.DataFrame, engine: Engine) -> None:
    """
    Two-step upsert into the normalised schema.

    Step 1 — register any new products (never overwrites an existing
    product's category; catalog corrections are out of scope).

    Step 2 — upsert the metrics rows themselves.
    """
    insert = _get_dialect_insert(engine)

    with engine.begin() as conn:
        # Step 1: register new products
        product_cols = ["product_id", "category", "subcategory", "brand"]
        products = (
            df[product_cols]
            .drop_duplicates("product_id")
            .to_dict("records")
        )
        prod_stmt = (
            insert(Product.__table__)
            .values(products)
            .on_conflict_do_nothing(index_elements=["product_id"])
        )
        conn.execute(prod_stmt)

        # Step 2: upsert metrics
        metrics = df.drop(columns=["category", "subcategory", "brand"]).to_dict("records")
        table = ProductMetricsDaily.__table__
        m_stmt = insert(table).values(metrics)
        update_cols = {
            c.name: m_stmt.excluded[c.name]
            for c in table.columns
            if c.name not in ("product_id", "date")
        }
        m_stmt = m_stmt.on_conflict_do_update(
            index_elements=["product_id", "date"],
            set_=update_cols,
        )
        conn.execute(m_stmt)
