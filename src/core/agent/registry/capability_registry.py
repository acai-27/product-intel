"""
Capability Registry — defines every tool the planner can invoke.

Each entry documents the tool's purpose, exact call boundaries,
input/output schemas, source module, and data dependency so the LLM planner
can reason about which tools to call and how to chain them.
"""

from typing import Any


CAPABILITY_REGISTRY: dict[str, dict[str, Any]] = {
    # ── Forecasting ──────────────────────────────────────────────────────
    "forecast_predict": {
        "description": "EXACTLY forecasts future revenue, profit, and orders for a known product over a given horizon. DOES NOT explain historical causes, detect anomalies, or optimize settings. Use ONLY to get future projected numbers.",
        "when_to_call": "Call when the user asks for future forecast/prediction/projection for a known product. If product_id is unknown, first discover it with nl2sql_query or ask clarification.",
        "input_schema": {
            "product_id": {"type": "str", "required": True},
            "horizon_days": {"type": "int", "required": False, "default": 30},
        },
        "output_schema": "{ forecast_total_revenue: float, forecast_total_profit: float, forecast_total_orders: float, daily_details: [{date, revenue, profit, orders}] }",
        "chains_into": ["forecast_explain_drivers", "simulate_scenario", "decision_ask"],
        "source_module": "src.core.forecaster.ProductForecaster.forecast",
        "requires_data": True,
    },

    # ── Explainability ───────────────────────────────────────────────────
    "forecast_explain_drivers": {
        "description": "EXACTLY computes SHAP feature importance for one product, one metric, and one specific date. It tells you WHY a metric changed on that day. DOES NOT forecast, simulate, or aggregate multiple products.",
        "when_to_call": "Call when the user asks why a metric changed for a known product/date, or after a prior step discovers product_id and date.",
        "input_schema": {
            "product_id": {"type": "str", "required": True},
            "target_metric": {"type": "str", "required": False, "default": "revenue", "options": ["revenue", "profit", "orders", "conversion_rate", "retention_rate"]},
            "date": {"type": "str (YYYY-MM-DD)", "required": True},
        },
        "output_schema": "{ prediction_value: float, base_value: float, explanation_summary: str, positive_drivers: [{feature, clean_name, shap_value}], negative_drivers: [{feature, clean_name, shap_value}] }",
        "chains_into": ["decision_ask"],
        "source_module": "src.core.explainer.PredictionExplainer.explain_prediction",
        "requires_data": True,
    },
    "explain_global": {
        "description": "EXACTLY computes the global feature importance across all products for a target metric over the entire dataset. DOES NOT explain specific dates or specific products.",
        "when_to_call": "Call when the user asks generally what drives a metric, not for a specific product/date incident.",
        "input_schema": {
            "target_metric": {"type": "str", "required": False, "default": "revenue"},
        },
        "output_schema": "[{ feature: str, clean_name: str, importance_value: float }]",
        "chains_into": ["decision_ask"],
        "source_module": "src.core.explainer.PredictionExplainer.get_global_importance",
        "requires_data": False,
    },

    # ── Scenario Simulation ──────────────────────────────────────────────
    "simulate_scenario": {
        "description": "EXACTLY simulates future KPI impacts when explicitly given lever changes (e.g. discount +5%, shipping -10%). DOES NOT find optimal parameters or explain the past.",
        "when_to_call": "Call when the user provides explicit what-if changes such as discount, marketing, shipping, or price changes for a product.",
        "input_schema": {
            "product_id": {"type": "str", "required": True},
            "horizon_days": {"type": "int", "required": False, "default": 30},
            "changes": {"type": "list[str]", "required": True, "examples": ["discount +5%", "marketing -10%", "shipping +20", "price =500"]},
        },
        "output_schema": "{ product_id: str, kpis: { revenue: {baseline, simulated, absolute_difference, percentage_difference, impact}, ... }, daily_comparison: {...} }",
        "chains_into": ["decision_ask"],
        "source_module": "src.core.simulator.ScenarioSimulator.evaluate_scenario",
        "requires_data": True,
    },

    # ── Optimization ─────────────────────────────────────────────────────
    "optimize_parameters": {
        "description": "EXACTLY finds the best mathematical parameters (discount, marketing) to maximize a target KPI. DOES NOT simulate custom scenarios or explain anomalies.",
        "when_to_call": "Call when the user asks for optimal discount/marketing settings for a known product and target metric.",
        "input_schema": {
            "product_id": {"type": "str", "required": True},
            "target_metric": {"type": "str", "required": False, "default": "revenue"},
            "horizon_days": {"type": "int", "required": False, "default": 30},
            "max_discount_pct": {"type": "float", "required": False, "default": 0.30},
            "max_marketing_budget": {"type": "float", "required": False, "default": 250.0},
        },
        "output_schema": "{ optimal_parameters: {discount_pct, marketing_spend, price}, baseline_forecast_sum: float, optimized_forecast_sum: float, percentage_improvement: float }",
        "chains_into": ["simulate_scenario", "decision_ask"],
        "source_module": "src.core.optimizer.RevenueOptimizer.optimize_parameters",
        "requires_data": True,
    },

    # ── Sensitivity ──────────────────────────────────────────────────────
    "sensitivity_estimate": {
        "description": "EXACTLY estimates the elasticity (sensitivity score) of a single product to levers like price, marketing, discount. DOES NOT optimize or simulate them.",
        "when_to_call": "Call when the user asks how sensitive one product is to levers such as price, marketing, discount, shipping, inventory, or retention.",
        "input_schema": {
            "product_id": {"type": "str", "required": True},
            "horizon_days": {"type": "int", "required": False, "default": 30},
        },
        "output_schema": "{ marketing: {elasticity_score, expected_impact, confidence}, discount: {...}, shipping: {...}, price: {...}, inventory: {...}, return: {...} }",
        "chains_into": ["decision_ask", "optimize_parameters"],
        "source_module": "src.core.sensitivity.SensitivityEngine.calculate_sensitivity",
        "requires_data": True,
    },

    # ── Analytics Suite ──────────────────────────────────────────────────
    "analytics_kpi": {
        "description": "EXACTLY computes aggregate KPI totals (sums/averages) across the dataset matching filters. DOES NOT rank products, detect anomalies, or forecast.",
        "when_to_call": "Call for aggregate KPI summaries over optional product/category/date filters, not for rankings or explanations.",
        "input_schema": {
            "product_id": {"type": "str", "required": False},
            "category": {"type": "str", "required": False},
            "start_date": {"type": "str (YYYY-MM-DD)", "required": False},
            "end_date": {"type": "str (YYYY-MM-DD)", "required": False},
        },
        "output_schema": "{ total_revenue, total_profit, total_orders, avg_conversion_rate, avg_retention_rate, ... }",
        "chains_into": ["analysis_compare"],
        "source_module": "src.core.analytics.engine.AnalyticsEngine.get_kpis",
        "requires_data": True,
    },
    "analytics_trend": {
        "description": "EXACTLY computes historical trend slope, r-squared, and growth rates for a metric. DOES NOT compare different date periods side-by-side or explain the trend.",
        "when_to_call": "Call for historical trend/growth/slope of a metric over time.",
        "input_schema": {
            "metric": {"type": "str", "required": False, "default": "revenue"},
            "product_id": {"type": "str", "required": False},
            "start_date": {"type": "str (YYYY-MM-DD)", "required": False},
            "end_date": {"type": "str (YYYY-MM-DD)", "required": False},
        },
        "output_schema": "{ slope, r_squared, growth_rate, daily_values[] }",
        "chains_into": ["decision_ask"],
        "source_module": "src.core.analytics.engine.AnalyticsEngine.get_trends",
        "requires_data": True,
    },
    "analytics_benchmark": {
        "description": "EXACTLY computes percentile rankings comparing a single product's metrics against its category and global averages. DOES NOT find the 'best' or 'worst' products.",
        "when_to_call": "Call to compare one known product against category/global averages.",
        "input_schema": {
            "product_id": {"type": "str", "required": True},
            "start_date": {"type": "str (YYYY-MM-DD)", "required": False},
            "end_date": {"type": "str (YYYY-MM-DD)", "required": False},
        },
        "output_schema": "{ product_metrics, category_avg, global_avg, percentile_rank }",
        "chains_into": ["decision_ask"],
        "source_module": "src.core.analytics.engine.AnalyticsEngine.get_benchmarks",
        "requires_data": True,
    },
    "analytics_seasonality": {
        "description": "EXACTLY computes day-of-week, weekend, and monthly seasonality coefficients. DOES NOT compute general trends.",
        "when_to_call": "Call for day-of-week, weekend, or monthly seasonality questions.",
        "input_schema": {
            "product_id": {"type": "str", "required": False},
            "category": {"type": "str", "required": False},
            "start_date": {"type": "str (YYYY-MM-DD)", "required": False},
            "end_date": {"type": "str (YYYY-MM-DD)", "required": False},
        },
        "output_schema": "{ day_of_week_pattern, monthly_pattern, weekend_effect }",
        "chains_into": ["decision_ask"],
        "source_module": "src.core.analytics.engine.AnalyticsEngine.get_seasonality",
        "requires_data": True,
    },
    "analytics_channel": {
        "description": "EXACTLY computes sales metrics separated by distribution channel. DOES NOT provide general KPI totals.",
        "when_to_call": "Call for channel mix/performance questions across Amazon, Website, Nykaa, and Mobile App.",
        "input_schema": {
            "product_id": {"type": "str", "required": False},
            "category": {"type": "str", "required": False},
            "start_date": {"type": "str (YYYY-MM-DD)", "required": False},
            "end_date": {"type": "str (YYYY-MM-DD)", "required": False},
        },
        "output_schema": "{ channel_breakdown[] }",
        "chains_into": ["decision_ask"],
        "source_module": "src.core.analytics.engine.AnalyticsEngine.get_channels",
        "requires_data": True,
    },
    "analytics_campaign": {
        "description": "EXACTLY computes marketing ROI and campaign spend metrics. DOES NOT optimize future marketing spend.",
        "when_to_call": "Call for campaign spend, allocation, and ROI questions.",
        "input_schema": {
            "product_id": {"type": "str", "required": False},
            "category": {"type": "str", "required": False},
            "start_date": {"type": "str (YYYY-MM-DD)", "required": False},
            "end_date": {"type": "str (YYYY-MM-DD)", "required": False},
        },
        "output_schema": "{ campaign_summary, roi_metrics }",
        "chains_into": ["decision_ask", "optimize_parameters"],
        "source_module": "src.core.analytics.engine.AnalyticsEngine.get_campaigns",
        "requires_data": True,
    },
    "analytics_inventory": {
        "description": "EXACTLY computes stock turnover rates and stockout risk probabilities. DOES NOT calculate revenue or shipping metrics.",
        "when_to_call": "Call for stock, turnover, inventory, or stockout-risk questions for a known product.",
        "input_schema": {
            "product_id": {"type": "str", "required": True},
            "start_date": {"type": "str (YYYY-MM-DD)", "required": False},
            "end_date": {"type": "str (YYYY-MM-DD)", "required": False},
        },
        "output_schema": "{ stock_turnover, stockout_risk, avg_inventory }",
        "chains_into": ["decision_ask"],
        "source_module": "src.core.analytics.engine.AnalyticsEngine.get_inventory",
        "requires_data": True,
    },
    "analytics_customer": {
        "description": "EXACTLY computes customer LTV, active user counts, and age group demographics. DOES NOT handle product-centric metrics like margin or stock.",
        "when_to_call": "Call for LTV, active users, retention/customer composition, or age-group questions.",
        "input_schema": {
            "product_id": {"type": "str", "required": False},
            "category": {"type": "str", "required": False},
            "start_date": {"type": "str (YYYY-MM-DD)", "required": False},
            "end_date": {"type": "str (YYYY-MM-DD)", "required": False},
        },
        "output_schema": "{ ltv_estimate, active_users, age_groups }",
        "chains_into": ["decision_ask"],
        "source_module": "src.core.analytics.engine.AnalyticsEngine.get_customers",
        "requires_data": True,
    },
    "analytics_marketing": {
        "description": "EXACTLY computes generic marketing performance (ROAS, CTR, spend correlation). DOES NOT explain specific drops or optimize future spend.",
        "when_to_call": "Call for ROAS, CTR, or marketing-spend correlation questions.",
        "input_schema": {
            "product_id": {"type": "str", "required": False},
            "category": {"type": "str", "required": False},
            "start_date": {"type": "str (YYYY-MM-DD)", "required": False},
            "end_date": {"type": "str (YYYY-MM-DD)", "required": False},
        },
        "output_schema": "{ roas, ctr, spend_revenue_correlation }",
        "chains_into": ["decision_ask", "optimize_parameters"],
        "source_module": "src.core.analytics.engine.AnalyticsEngine.get_marketing",
        "requires_data": True,
    },
    "analytics_pricing": {
        "description": "EXACTLY computes performance grouped by discount buckets and raw price elasticity. DOES NOT recommend optimal discounts.",
        "when_to_call": "Call for discount bucket, pricing, and price elasticity questions.",
        "input_schema": {
            "product_id": {"type": "str", "required": False},
            "category": {"type": "str", "required": False},
            "start_date": {"type": "str (YYYY-MM-DD)", "required": False},
            "end_date": {"type": "str (YYYY-MM-DD)", "required": False},
        },
        "output_schema": "{ discount_bucket_performance, price_elasticity }",
        "chains_into": ["decision_ask", "optimize_parameters", "simulate_scenario"],
        "source_module": "src.core.analytics.engine.AnalyticsEngine.get_pricing",
        "requires_data": True,
    },

    # ── Anomaly Detection ────────────────────────────────────────────────
    "anomaly_detect": {
        "description": "EXACTLY runs a statistical check to see if a single product's KPI is an anomaly on a specific date. DOES NOT explain WHY the anomaly happened.",
        "when_to_call": "Call to inspect anomaly status for a known product/KPI/date. If product is unknown, call anomaly_rank_products first.",
        "input_schema": {
            "product_id": {"type": "str", "required": True},
            "target_date": {"type": "str (YYYY-MM-DD)", "required": True},
            "kpi": {"type": "str", "required": False, "default": "revenue"},
        },
        "output_schema": "{ summary: {total_points, anomaly_count}, graph_data: [{date, value, is_anomaly, classification, deviation_pct}], anomalies: [...] }",
        "chains_into": ["forecast_explain_drivers", "decision_ask"],
        "source_module": "src.core.new_anomaly.engine.AnomalyDetectionEngineV2.run_detection",
        "requires_data": True,
    },
    "anomaly_rank_products": {
        "description": "EXACTLY returns a ranked list of the most anomalous products for a specific date and KPI. DOES NOT detect anomalies over time.",
        "when_to_call": "Call to rank products by anomaly risk for a KPI/date or to discover product_id before anomaly_detect.",
        "input_schema": {
            "date": {"type": "str (YYYY-MM-DD)", "required": True},
            "kpi": {"type": "str", "required": False, "default": "revenue"},
        },
        "output_schema": "{ top_10_critical_products: [{product_id, kpi, severity_score, status, percent_change}] }",
        "chains_into": ["anomaly_detect", "forecast_explain_drivers"],
        "source_module": "src.core.new_anomaly.engine.AnomalyDetectionEngineV2.get_top_products",
        "requires_data": True,
    },

    # ── Business Analysis ────────────────────────────────────────────────
    "analysis_compare": {
        "description": "EXACTLY computes the percentage difference of KPIs between two explicitly defined date periods. DOES NOT explain the reasons for the difference.",
        "when_to_call": "Call when the user asks to compare two explicit date periods.",
        "input_schema": {
            "period1_start": {"type": "str (YYYY-MM-DD)", "required": True},
            "period1_end": {"type": "str (YYYY-MM-DD)", "required": True},
            "period2_start": {"type": "str (YYYY-MM-DD)", "required": True},
            "period2_end": {"type": "str (YYYY-MM-DD)", "required": True},
            "product_id": {"type": "str", "required": False},
        },
        "output_schema": "{ metrics_comparison: {revenue: {period1_sum, period2_sum, percentage_change}, ...}, drivers_summary[] }",
        "chains_into": ["forecast_explain_drivers", "decision_ask"],
        "source_module": "src.core.analyzer.BusinessAnalyzer.compare_periods",
        "requires_data": True,
    },
    "analysis_declining": {
        "description": "EXACTLY returns a list of products whose metric slope is negative over the lookback window. DOES NOT explain why they are declining.",
        "when_to_call": "Call when the user asks which products are declining over a lookback window.",
        "input_schema": {
            "lookback_days": {"type": "int", "required": False, "default": 30},
            "metric": {"type": "str", "required": False, "default": "revenue"},
        },
        "output_schema": "{ declining_products: [{product_id, slope, percentage_change, r_squared}] }",
        "chains_into": ["forecast_explain_drivers", "anomaly_detect", "decision_ask"],
        "source_module": "src.core.analyzer.BusinessAnalyzer.detect_declining_products",
        "requires_data": True,
    },

    # ── Decision Intelligence ────────────────────────────────────────────
    "decision_ask": {
        "description": "EXACTLY generates strategic recommendations, hypotheses, and action plans based on upstream context. MUST be called at the end of a chain. DOES NOT pull database data natively.",
        "when_to_call": "Call for strategic recommendations, should-we questions, decisions, or complex business advice after enough context is known.",
        "input_schema": {
            "query": {"type": "str", "required": True},
            "product_id": {"type": "str", "required": False},
            "session_id": {"type": "str", "required": False},
        },
        "output_schema": "{ ranked_hypotheses[], recommendations[], explanation: str }",
        "chains_into": [],
        "source_module": "src.core.decision.manager.DecisionManager.process_decision_flow",
        "requires_data": True,
    },

    # ── NL2SQL Data Lookup ───────────────────────────────────────────────
    "nl2sql_query": {
        "description": "EXACTLY converts a natural language request into SQL to fetch, aggregate, count, or rank database rows. Use this to find specific product IDs, dates, or factual totals before running analytical tools. DOES NOT forecast, explain, simulate, or recommend.",
        "when_to_call": "Call for factual lookups, rankings, counts, lists, aggregations, or to discover product_id/date/category for later steps.",
        "input_schema": {
            "query": {"type": "str", "required": True},
        },
        "output_schema": "{ query: str, sql: str, columns: [str], rows: [dict], row_count: int, truncated: bool }",
        "chains_into": ["forecast_explain_drivers", "analytics_trend", "anomaly_detect", "analysis_compare", "forecast_predict"],
        "source_module": "src.core.nl2sql.engine.NL2SQLEngine.ask",
        "requires_data": False,
    },

    # ── History Repository ───────────────────────────────────────────────
    "repository_search": {
        "description": "EXACTLY performs a semantic search over historical experiment/A-B test reports for past evidence matching the query. DOES NOT query real-time product metrics.",
        "when_to_call": "Call when the user asks for related past reports, experiments, or historical evidence.",
        "input_schema": {
            "query": {"type": "str", "required": True},
        },
        "output_schema": "{ results_found: int, items: [{score, experiment_id, type, change_summary, outcome, structured_report}] }",
        "chains_into": ["decision_ask"],
        "source_module": "src.core.history.manager.HistoryManager.semantic_search",
        "requires_data": False,
    },
    "repository_extract": {
        "description": "EXACTLY aggregates topic-level learnings from past experiments (e.g. all pricing learnings). DOES NOT return current product performance.",
        "when_to_call": "Call when the user asks for summarized learnings or strategies from previous experiments by topic.",
        "input_schema": {
            "query": {"type": "str", "required": False},
            "category": {"type": "str", "required": False, "options": ["pricing", "checkout", "discount", "shipping", "marketing"]},
        },
        "output_schema": "{ insights, successful_strategies, learnings }",
        "chains_into": ["decision_ask", "simulate_scenario"],
        "source_module": "src.core.history.manager.HistoryManager.extract_topic_insights",
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
