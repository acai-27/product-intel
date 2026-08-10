"""
Tool Nodes — thin wrappers that invoke the actual core engines.

Each function takes step params and the AppState engines, executes
the corresponding module, and returns the result dict.
"""

import re
from typing import Any

import pandas as pd

from src.utils.logger import setup_logger

logger = setup_logger("tool_nodes")


def execute_tool(
    tool_id: str,
    params: dict[str, Any],
    engines: dict[str, Any],
) -> dict[str, Any]:
    """Dispatch a tool call to the corresponding core engine."""
    handler = _TOOL_HANDLERS.get(tool_id)
    if not handler:
        raise ValueError(f"Unknown tool_id: {tool_id}")
    return handler(params, engines)


# ── Individual tool handlers ─────────────────────────────────────────────


def _forecast(params: dict[str, Any], engines: dict[str, Any]) -> dict[str, Any]:
    """Run the forecaster."""
    df = _get_data(params, engines)
    forecast_df = engines["forecaster"].forecast(
        historical_df=df,
        product_id=params["product_id"],
        horizon_days=int(params.get("horizon_days", 30)),
    )
    records = []
    for _, row in forecast_df.head(10).iterrows():
        records.append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "revenue": round(float(row["revenue"]), 2),
            "profit": round(float(row["profit"]), 2),
            "orders": round(float(row["orders"]), 2),
        })
    return {
        "product_id": params["product_id"],
        "horizon_days": int(params.get("horizon_days", 30)),
        "forecast_total_revenue": round(float(forecast_df["revenue"].sum()), 2),
        "forecast_total_profit": round(float(forecast_df["profit"].sum()), 2),
        "forecast_total_orders": round(float(forecast_df["orders"].sum()), 2),
        "daily_details": records,
    }


def _explain(params: dict[str, Any], engines: dict[str, Any]) -> dict[str, Any]:
    """Run the explainer."""
    df = _get_data(params, engines)
    return engines["explainer"].explain_prediction(
        historical_df=df,
        product_id=params["product_id"],
        target_metric=params.get("target_metric", "revenue"),
        date=params["date"],
    )


def _explain_global(params: dict[str, Any], engines: dict[str, Any]) -> dict[str, Any]:
    """Run global importance."""
    metric = params.get("target_metric", "revenue")
    return {
        "target_metric": metric,
        "global_importance": engines["explainer"].get_global_importance(metric),
    }


def _simulate(params: dict[str, Any], engines: dict[str, Any]) -> dict[str, Any]:
    """Run scenario simulation."""
    df = _get_data(params, engines)
    changes = params.get("changes", ["discount +5%", "marketing +10%"])
    if isinstance(changes, str):
        changes = [c.strip() for c in changes.split(",")]
    return engines["simulator"].evaluate_scenario(
        historical_df=df,
        product_id=params["product_id"],
        horizon_days=int(params.get("horizon_days", 30)),
        changes=changes,
    )


def _anomaly_detect(params: dict[str, Any], engines: dict[str, Any]) -> dict[str, Any]:
    """Run anomaly detection."""
    return engines["anomaly_engine"].run_detection(
        product_id=params["product_id"],
        target_date=params["target_date"],
        kpi=params.get("kpi", "revenue"),
    )


def _anomaly_rank(params: dict[str, Any], engines: dict[str, Any]) -> dict[str, Any]:
    """Run anomaly ranking."""
    return engines["anomaly_engine"].get_top_products(
        date=params["date"],
        kpi=params.get("kpi", "revenue"),
    )


def _nl2sql_query(params: dict[str, Any], engines: dict[str, Any]) -> dict[str, Any]:
    """Answer a factual data question via NL2SQL."""
    nl2sql_engine = engines.get("nl2sql_engine")
    if nl2sql_engine is None:
        raise RuntimeError("NL2SQL engine is not initialized.")
    query = params.get("query", "")
    if isinstance(query, str) and query.strip().lower().startswith("select"):
        from src.core.nl2sql.executor import execute_sql
        from src.core.nl2sql.validator import validate_sql

        db_engine = getattr(nl2sql_engine, "_db_engine", None)
        if db_engine is None:
            raise RuntimeError("NL2SQL engine does not expose a database engine for direct SQL execution.")
        validated_sql = validate_sql(query, dialect=db_engine.dialect.name)
        result = execute_sql(db_engine, validated_sql)
        return {
            "query": query,
            "sql": validated_sql,
            "columns": result["columns"],
            "rows": result["rows"],
            "row_count": result["row_count"],
            "truncated": result["truncated"],
        }
    return nl2sql_engine.ask(query)




# ── Data helper ──────────────────────────────────────────────────────────


def _get_data(params: dict[str, Any], engines: dict[str, Any]) -> pd.DataFrame:
    """Fetch historical data, filtering by params if provided."""
    from src.api.dependencies import get_historical_df_from_db
    return get_historical_df_from_db(
        start_date=params.get("start_date") or params.get("period1_start"),
        end_date=params.get("end_date") or params.get("period2_end"),
        product_id=params.get("product_id"),
        category=params.get("category"),
    )


# ── Handler registry ─────────────────────────────────────────────────────

_TOOL_HANDLERS: dict[str, Any] = {
    "forecast_predict": _forecast,
    "forecast_explain_drivers": _explain,
    "explain_global": _explain_global,
    "simulate_scenario": _simulate,
    "anomaly_detect": _anomaly_detect,
    "anomaly_rank_products": _anomaly_rank,
    "nl2sql_query": _nl2sql_query,
}
