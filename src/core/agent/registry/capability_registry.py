"""
Capability Registry - final scoped tools available to the LangGraph planner.
"""

from typing import Any

CAPABILITY_REGISTRY: dict[str, dict[str, Any]] = {
    "forecast_predict": {
        "description": "Forecasts future revenue, profit, and orders for a known product over a given horizon.",
        "when_to_call": "Call when the user asks for future forecast, prediction, or projection for a known product.",
        "input_schema": {
            "product_id": {"type": "str", "required": True},
            "horizon_days": {"type": "int", "required": False, "default": 30},
        },
        "output_schema": "{ forecast_total_revenue: float, forecast_total_profit: float, forecast_total_orders: float, daily_details: [{date, revenue, profit, orders}] }",
        "chains_into": ["forecast_explain_drivers", "simulate_scenario"],
        "source_module": "src.core.forecaster.ProductForecaster.forecast",
        "requires_data": True,
    },
    "forecast_explain_drivers": {
        "description": "Computes SHAP feature attribution for one product, one metric, and one date. Returns attribution, not proven causation.",
        "when_to_call": "Call when the user asks why a metric or forecast is high/low for a known product/date.",
        "input_schema": {
            "product_id": {"type": "str", "required": True},
            "target_metric": {"type": "str", "required": False, "default": "revenue", "options": ["revenue", "profit", "orders", "conversion_rate", "retention_rate"]},
            "date": {"type": "str (YYYY-MM-DD)", "required": True},
        },
        "output_schema": "{ prediction_value: float, base_value: float, explanation_summary: str, positive_drivers: [{feature, clean_name, shap_value}], negative_drivers: [...] }",
        "chains_into": [],
        "source_module": "src.core.explainer.PredictionExplainer.explain_prediction",
        "requires_data": True,
    },
    "explain_global": {
        "description": "Computes global feature importance for a target metric.",
        "when_to_call": "Call when the user asks generally what drives a metric, without a specific product/date incident.",
        "input_schema": {
            "target_metric": {"type": "str", "required": False, "default": "revenue"},
        },
        "output_schema": "[{ feature: str, clean_name: str, importance_value: float }]",
        "chains_into": [],
        "source_module": "src.core.explainer.PredictionExplainer.get_global_importance",
        "requires_data": False,
    },
    "simulate_scenario": {
        "description": "Simulates future KPI impacts for explicit lever changes such as discount, marketing, shipping, or price.",
        "when_to_call": "Call when the user gives an explicit what-if change to test. Does not optimize or recommend a best setting.",
        "input_schema": {
            "product_id": {"type": "str", "required": True},
            "horizon_days": {"type": "int", "required": False, "default": 30},
            "changes": {"type": "list[str]", "required": True, "examples": ["discount +5%", "marketing -10%", "shipping +20", "price =500"]},
        },
        "output_schema": "{ product_id: str, kpis: { revenue: {baseline, simulated, absolute_difference, percentage_difference, impact}, ... }, daily_comparison: {...} }",
        "chains_into": [],
        "source_module": "src.core.simulator.ScenarioSimulator.evaluate_scenario",
        "requires_data": True,
    },
    "anomaly_detect": {
        "description": "Runs Isolation Forest anomaly detection for one product, KPI, and date.",
        "when_to_call": "Call to inspect whether a known product/KPI/date is anomalous.",
        "input_schema": {
            "product_id": {"type": "str", "required": True},
            "target_date": {"type": "str (YYYY-MM-DD)", "required": True},
            "kpi": {"type": "str", "required": False, "default": "revenue"},
        },
        "output_schema": "{ summary: {total_points, anomaly_count}, graph_data: [{date, value, is_anomaly, classification, deviation_pct}], anomalies: [...] }",
        "chains_into": ["forecast_explain_drivers"],
        "source_module": "src.core.new_anomaly.engine.AnomalyDetectionEngineV2.run_detection",
        "requires_data": True,
    },
    "anomaly_rank_products": {
        "description": "Ranks products by anomaly severity for a specific date and KPI.",
        "when_to_call": "Call to discover the most anomalous products for a date/KPI or to discover product_id before anomaly_detect.",
        "input_schema": {
            "date": {"type": "str (YYYY-MM-DD)", "required": True},
            "kpi": {"type": "str", "required": False, "default": "revenue"},
        },
        "output_schema": "{ top_10_critical_products: [{product_id, kpi, severity_score, status, percent_change}] }",
        "chains_into": ["anomaly_detect", "forecast_explain_drivers"],
        "source_module": "src.core.new_anomaly.engine.AnomalyDetectionEngineV2.get_top_products",
        "requires_data": True,
    },
    "nl2sql_query": {
        "description": "Converts a natural language factual lookup into validated read-only SQL and returns tabular results.",
        "when_to_call": "Call for factual lookups, rankings, counts, lists, aggregations, or to discover product_id/date/category for later final-scope tools.",
        "input_schema": {
            "query": {"type": "str", "required": True},
        },
        "output_schema": "{ query: str, sql: str, columns: [str], rows: [dict], row_count: int, truncated: bool }",
        "chains_into": ["forecast_explain_drivers", "anomaly_detect", "forecast_predict"],
        "source_module": "src.core.nl2sql.engine.NL2SQLEngine.ask",
        "requires_data": False,
    },
}


def get_tool_descriptions_for_prompt() -> str:
    """Format the registry into a text block suitable for injection into LLM prompts."""
    lines: list[str] = []
    for tool_id, spec in CAPABILITY_REGISTRY.items():
        params = ", ".join(
            f"{k}: {v['type']}" + (f" (default={v['default']})" if "default" in v else "")
            for k, v in spec["input_schema"].items()
        )
        chains = ", ".join(spec.get("chains_into", []))
        desc = f"- {tool_id}({params}): {spec['description']}"
        desc += f"\n  When to call: {spec.get('when_to_call', 'Use when this exact capability is requested.')}"
        desc += f"\n  Output Schema: {spec.get('output_schema', '{}')}"
        if chains:
            desc += f"\n  Chains Into: [{chains}]"
        lines.append(desc)
    return "\n".join(lines)
