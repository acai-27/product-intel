"""
Standard DAG templates for final scoped intents.
"""

from typing import Any

STANDARD_DAGS: dict[str, list[dict[str, Any]]] = {
    "forecast_request": [
        {"step_id": "s1", "tool_id": "forecast_predict", "params": {"product_id": "P001", "horizon_days": 30}, "depends_on": []},
    ],
    "explanation_request": [
        {"step_id": "s1", "tool_id": "forecast_explain_drivers", "params": {"product_id": "P001", "target_metric": "revenue"}, "depends_on": []},
    ],
    "scenario_simulation": [
        {"step_id": "s1", "tool_id": "simulate_scenario", "params": {"product_id": "P001", "horizon_days": 30}, "depends_on": []},
    ],
    "data_lookup": [
        {"step_id": "s1", "tool_id": "nl2sql_query", "params": {}, "depends_on": []},
    ],
    "anomaly_check": [
        {"step_id": "s1", "tool_id": "anomaly_detect", "params": {"product_id": "P001", "kpi": "revenue"}, "depends_on": []},
    ],
}
