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


def _optimize(params: dict[str, Any], engines: dict[str, Any]) -> dict[str, Any]:
    """Run parameter optimization."""
    df = _get_data(params, engines)
    return engines["optimizer"].optimize_parameters(
        historical_df=df,
        product_id=params["product_id"],
        horizon_days=int(params.get("horizon_days", 30)),
        target_metric=params.get("target_metric", "revenue"),
        max_discount_pct=float(params.get("max_discount_pct", 0.30)),
        max_marketing_budget=float(params.get("max_marketing_budget", 250.0)),
    )


def _sensitivity(params: dict[str, Any], engines: dict[str, Any]) -> dict[str, Any]:
    """Run sensitivity analysis."""
    df = _get_data(params, engines)
    return engines["sensitivity_engine"].calculate_sensitivity(
        historical_df=df,
        product_id=params["product_id"],
        horizon_days=int(params.get("horizon_days", 30)),
    )


def _analytics(method_name: str):
    """Factory for analytics engine methods."""
    def handler(params: dict[str, Any], engines: dict[str, Any]) -> dict[str, Any]:
        method = getattr(engines["analytics_engine"], method_name)
        # Filter params to only those the method accepts
        return method(**{
            k: v for k, v in params.items()
            if k in ("product_id", "category", "start_date", "end_date", "metric", "granularity")
        })
    return handler


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


def _analysis_compare(params: dict[str, Any], engines: dict[str, Any]) -> dict[str, Any]:
    """Run period comparison."""
    df = _get_data(params, engines)
    return engines["analyzer"].compare_periods(
        df=df,
        period1_start=params.get("period1_start", "2025-01-01"),
        period1_end=params.get("period1_end", "2025-01-15"),
        period2_start=params.get("period2_start", "2025-01-16"),
        period2_end=params.get("period2_end", "2025-01-30"),
        product_id=params.get("product_id"),
    )


def _analysis_declining(params: dict[str, Any], engines: dict[str, Any]) -> dict[str, Any]:
    """Find declining products."""
    df = _get_data(params, engines)
    return {
        "metric": params.get("metric", "revenue"),
        "lookback_days": int(params.get("lookback_days", 30)),
        "declining_products": engines["analyzer"].detect_declining_products(
            df=df,
            lookback_days=int(params.get("lookback_days", 30)),
            metric=params.get("metric", "revenue"),
        )[:10],
    }


def _decision_ask(params: dict[str, Any], engines: dict[str, Any]) -> dict[str, Any]:
    """Run decision intelligence flow."""
    from src.core.history.storage.database import SessionLocal
    from src.core.decision.manager import DecisionManager
    from src.core.history.manager import HistoryManager

    df = _get_data(params, engines)
    db = SessionLocal()
    try:
        history_mgr = HistoryManager(db, encoder=engines.get("history_encoder"))
        manager = DecisionManager(
            db=db,
            df_historical=df,
            forecaster=engines["forecaster"],
            sensitivity_engine=engines["sensitivity_engine"],
            simulator=engines["simulator"],
            history_manager=history_mgr,
            explainer=engines.get("explainer"),
            llm_client=engines.get("llm_client"),
        )
        return manager.process_decision_flow(
            query=params.get("query", ""),
            product_id=params.get("product_id"),
            session_id=params.get("session_id"),
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


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
        validated_sql = validate_sql(query)
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


def _repository_search(params: dict[str, Any], engines: dict[str, Any]) -> dict[str, Any]:
    """Search the history repository."""
    from src.core.history.storage.database import SessionLocal
    from src.core.history.manager import HistoryManager

    db = SessionLocal()
    try:
        mgr = HistoryManager(db, encoder=engines.get("history_encoder"))
        results = mgr.semantic_search(params.get("query", ""), limit=5)
        items = []
        for res in results:
            items.append({
                "score": res["score"],
                "experiment_id": res["experiment"].experiment_id,
                "type": res["experiment"].type,
                "change_summary": res["experiment"].change_summary,
                "outcome": res["experiment"].outcome,
                "structured_report": res["report"].structured_json,
            })
        return {"query": params.get("query", ""), "results_found": len(items), "items": items}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _repository_extract(params: dict[str, Any], engines: dict[str, Any]) -> dict[str, Any]:
    """Extract topic insights from the repository."""
    from src.core.history.storage.database import SessionLocal
    from src.core.history.manager import HistoryManager

    topic = params.get("category") or params.get("query") or "pricing"
    db = SessionLocal()
    try:
        mgr = HistoryManager(db, encoder=engines.get("history_encoder"))
        return mgr.extract_topic_insights(topic)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


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
    "optimize_parameters": _optimize,
    "sensitivity_estimate": _sensitivity,
    "analytics_kpi": _analytics("get_kpis"),
    "analytics_trend": _analytics("get_trends"),
    "analytics_benchmark": _analytics("get_benchmarks"),
    "analytics_seasonality": _analytics("get_seasonality"),
    "analytics_channel": _analytics("get_channels"),
    "analytics_campaign": _analytics("get_campaigns"),
    "analytics_inventory": _analytics("get_inventory"),
    "analytics_customer": _analytics("get_customers"),
    "analytics_marketing": _analytics("get_marketing"),
    "analytics_pricing": _analytics("get_pricing"),
    "anomaly_detect": _anomaly_detect,
    "anomaly_rank_products": _anomaly_rank,
    "analysis_compare": _analysis_compare,
    "analysis_declining": _analysis_declining,
    "decision_ask": _decision_ask,
    "nl2sql_query": _nl2sql_query,
    "repository_search": _repository_search,
    "repository_extract": _repository_extract,
}
