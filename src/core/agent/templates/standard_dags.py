"""
Standard DAG Templates — pre-compiled execution plans for common intents.

These are loaded in-memory at startup for zero-latency planning.
Each template is a list of DAG steps with tool_id, default params,
and dependency ordering.
"""

from typing import Any

STANDARD_DAGS: dict[str, list[dict[str, Any]]] = {

    # ── Single-step DAGs ─────────────────────────────────────────────────

    "forecast_request": [
        {"step_id": "s1", "tool_id": "forecast_predict", "params": {"product_id": "P001", "horizon_days": 30}, "depends_on": []},
    ],

    "explanation_request": [
        {"step_id": "s1", "tool_id": "forecast_explain_drivers", "params": {"product_id": "P001", "target_metric": "revenue"}, "depends_on": []},
    ],

    "scenario_simulation": [
        {"step_id": "s1", "tool_id": "simulate_scenario", "params": {"product_id": "P001", "horizon_days": 30}, "depends_on": []},
    ],

    "optimization_request": [
        {"step_id": "s1", "tool_id": "optimize_parameters", "params": {"product_id": "P001", "target_metric": "revenue", "horizon_days": 30}, "depends_on": []},
    ],

    "sensitivity_analysis": [
        {"step_id": "s1", "tool_id": "sensitivity_estimate", "params": {"product_id": "P001", "horizon_days": 30}, "depends_on": []},
    ],

    "kpi_summary": [
        {"step_id": "s1", "tool_id": "analytics_kpi", "params": {}, "depends_on": []},
    ],

    "data_lookup": [
        {"step_id": "s1", "tool_id": "nl2sql_query", "params": {}, "depends_on": []},
    ],

    "trend_analysis": [
        {"step_id": "s1", "tool_id": "analytics_trend", "params": {"metric": "revenue"}, "depends_on": []},
    ],

    "seasonality_analysis": [
        {"step_id": "s1", "tool_id": "analytics_seasonality", "params": {}, "depends_on": []},
    ],

    "channel_analysis": [
        {"step_id": "s1", "tool_id": "analytics_channel", "params": {}, "depends_on": []},
    ],

    "campaign_analysis": [
        {"step_id": "s1", "tool_id": "analytics_campaign", "params": {}, "depends_on": []},
    ],

    "inventory_check": [
        {"step_id": "s1", "tool_id": "analytics_inventory", "params": {"product_id": "P001"}, "depends_on": []},
    ],

    "customer_analysis": [
        {"step_id": "s1", "tool_id": "analytics_customer", "params": {}, "depends_on": []},
    ],

    "marketing_analysis": [
        {"step_id": "s1", "tool_id": "analytics_marketing", "params": {}, "depends_on": []},
    ],

    "pricing_analysis": [
        {"step_id": "s1", "tool_id": "analytics_pricing", "params": {}, "depends_on": []},
    ],

    "period_comparison": [
        {"step_id": "s1", "tool_id": "analysis_compare", "params": {}, "depends_on": []},
    ],

    "repository_search": [
        {"step_id": "s1", "tool_id": "repository_search", "params": {}, "depends_on": []},
    ],

    "decision_recommendation": [
        {"step_id": "s1", "tool_id": "decision_ask", "params": {"product_id": "P001"}, "depends_on": []},
    ],

    # ── Multi-step DAGs ──────────────────────────────────────────────────

    "anomaly_check": [
        {"step_id": "s1", "tool_id": "anomaly_detect", "params": {"product_id": "P001", "kpi": "revenue"}, "depends_on": []},
    ],
}
