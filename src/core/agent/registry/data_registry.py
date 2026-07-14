"""
Data Registry — provides the planner with knowledge of available data.

Dynamically queries the database/CSV to report available products,
categories, date ranges, metrics, and driver columns.
"""

import os
from functools import lru_cache
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text

from src.utils.logger import setup_logger

logger = setup_logger("data_registry")

# Static schema knowledge
METRICS = ["revenue", "profit", "orders", "conversion_rate", "retention_rate"]
DRIVERS = [
    "marketing_spend", "discount_pct", "shipping_fee",
    "avg_selling_price", "inventory_available", "traffic",
]
TABLE_NAME = "product_performance"
COLUMNS = [
    "date", "product_id", "category",
    *DRIVERS, *METRICS,
]
QUERYABLE_TABLE_DESCRIPTIONS = {
    "product_performance": "Daily product KPIs and business drivers. Primary table for revenue, profit, orders, marketing, inventory.",
    "events": "Business events such as anomalies, stockouts, and campaign changes.",
    "snapshots": "Daily aggregated business snapshots across all products.",
    "knowledge_base": "Synthesized business rules and patterns from past analyses.",
}
QUERYABLE_TABLES = sorted(QUERYABLE_TABLE_DESCRIPTIONS)


@lru_cache(maxsize=1)
def get_data_summary() -> dict[str, Any]:
    """Return a summary of what data is available for the planner."""
    try:
        return _get_db_summary()
    except Exception as e:
        logger.warning(f"Database summary query failed; falling back to CSV summary: {e}")
        csv_path = "temporal_dataset.csv"
        if os.path.exists(csv_path):
            return _get_csv_summary(csv_path)
        else:
            return _empty_summary()


def get_data_summary_for_prompt() -> str:
    """Format the data summary as a text block for LLM prompt injection."""
    summary = get_data_summary()
    table_summaries = "\n".join(
        f"  - {name}: {QUERYABLE_TABLE_DESCRIPTIONS[name]}"
        for name in QUERYABLE_TABLES
    )
    return (
        f"Primary table: {summary['table']}\n"
        f"Queryable tables (use nl2sql_query for ad-hoc factual questions):\n{table_summaries}\n"
        f"Available product IDs: {summary['product_ids']}\n"
        f"Available categories: {summary['categories']}\n"
        f"Date range: {summary['date_range']['min']} to {summary['date_range']['max']}\n"
        f"Total rows: {summary['total_rows']}\n"
        f"Predictable metrics: {summary['metrics']}\n"
        f"Controllable drivers: {summary['drivers']}"
    )


def _get_db_summary() -> dict[str, Any]:
    """Read planner context with lightweight aggregate queries, not SELECT *."""
    database_url = os.getenv("NEON_URL") or os.getenv("DATABASE_URL") or "sqlite:///data/historical_repository.db"
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args)

    with engine.connect() as conn:
        row = conn.execute(
            text(f"SELECT COUNT(*) AS total_rows, MIN(date) AS min_date, MAX(date) AS max_date FROM {TABLE_NAME}")
        ).mappings().one()
        product_ids = [
            r[0]
            for r in conn.execute(
                text(f"SELECT DISTINCT product_id FROM {TABLE_NAME} WHERE product_id IS NOT NULL ORDER BY product_id LIMIT 200")
            ).all()
        ]
        categories = [
            r[0]
            for r in conn.execute(
                text(f"SELECT DISTINCT category FROM {TABLE_NAME} WHERE category IS NOT NULL ORDER BY category LIMIT 200")
            ).all()
        ]

    total_rows = int(row["total_rows"] or 0)
    if total_rows == 0:
        return _empty_summary()

    return {
        "table": TABLE_NAME,
        "columns": COLUMNS,
        "metrics": METRICS,
        "drivers": DRIVERS,
        "queryable_tables": QUERYABLE_TABLES,
        "product_ids": product_ids,
        "categories": categories,
        "date_range": {
            "min": _date_to_str(row["min_date"]),
            "max": _date_to_str(row["max_date"]),
        },
        "total_rows": total_rows,
    }


def _get_csv_summary(csv_path: str) -> dict[str, Any]:
    """Fallback summary for local CSV without loading the full data table."""
    sample = pd.read_csv(csv_path, usecols=["product_id", "category"], nrows=5000)
    dates = pd.read_csv(csv_path, usecols=["date"])
    dates["date"] = pd.to_datetime(dates["date"], errors="coerce")

    return {
        "table": TABLE_NAME,
        "columns": COLUMNS,
        "metrics": METRICS,
        "drivers": DRIVERS,
        "queryable_tables": QUERYABLE_TABLES,
        "product_ids": sorted(sample["product_id"].dropna().unique().tolist())[:200],
        "categories": sorted(sample["category"].dropna().unique().tolist())[:200],
        "date_range": {
            "min": str(dates["date"].min().date()) if not dates["date"].dropna().empty else "N/A",
            "max": str(dates["date"].max().date()) if not dates["date"].dropna().empty else "N/A",
        },
        "total_rows": len(dates),
    }


def _date_to_str(value: Any) -> str:
    if value is None:
        return "N/A"
    try:
        return str(pd.to_datetime(value).date())
    except Exception:
        return str(value)


def _empty_summary() -> dict[str, Any]:
    """Fallback when no data source is available."""
    return {
        "table": TABLE_NAME,
        "columns": COLUMNS,
        "metrics": METRICS,
        "drivers": DRIVERS,
        "queryable_tables": QUERYABLE_TABLES,
        "product_ids": [],
        "categories": [],
        "date_range": {"min": "N/A", "max": "N/A"},
        "total_rows": 0,
    }
