"""
Response Validator Node.

Runs between the executor and synthesizer to verify that the executed DAG steps
produced complete, non-empty, and relevant results. Deterministic checks handle
plan coverage and NL2SQL alignment first; embeddings are only a fallback signal.
"""

from typing import Any
import re

import numpy as np

from src.core.agent.state import AgentState
from src.utils.logger import setup_logger

logger = setup_logger("validator")

_encoder = None

_METRIC_TERMS: dict[str, tuple[str, ...]] = {
    "profit": ("profit", "profitable", "margin"),
    "revenue": ("revenue", "sales", "selling"),
    "orders": ("orders", "order volume", "units sold"),
    "conversion_rate": ("conversion", "conversion rate"),
    "retention_rate": ("retention", "retention rate"),
    "inventory_available": ("inventory", "stock"),
    "marketing_spend": ("marketing", "ad spend", "spend"),
}

_COMPLEX_QUERY_TOOL_HINTS: tuple[tuple[re.Pattern[str], tuple[str, ...], str], ...] = (
    (re.compile(r"\b(forecast|predict|projection|next|future)\b", re.I), ("forecast_predict",), "forecasting"),
    (re.compile(r"\b(why|explain|driver|cause|root cause|diagnos)\b", re.I), ("forecast_explain_drivers", "decision_ask"), "explanation/diagnosis"),
    (re.compile(r"\b(should we|recommend|recommendation|decision|strategy|actionable)\b", re.I), ("decision_ask",), "decision recommendation"),
    (re.compile(r"\b(what if|what-if|simulate|simulation|scenario)\b", re.I), ("simulate_scenario", "decision_ask"), "scenario simulation"),
    (re.compile(r"\b(optimi[sz]e|maximi[sz]e|minimi[sz]e|best parameter|best discount|best price)\b", re.I), ("optimize_parameters",), "optimization"),
    (re.compile(r"\b(anomal|outlier|unusual|spike|drop)\b", re.I), ("anomaly_detect", "anomaly_rank_products", "forecast_explain_drivers", "decision_ask"), "anomaly/diagnosis"),
)

_RANKING_TERMS = re.compile(r"\b(top|highest|lowest|most|least|biggest|smallest|best|worst)\b", re.I)
_AGGREGATE_TERMS = re.compile(r"\b(total|sum|average|avg|count|how many)\b", re.I)


def _get_encoder() -> Any:
    global _encoder
    if _encoder is None:
        from src.core.history.embeddings.encoder import SentenceTransformerEncoder

        _encoder = SentenceTransformerEncoder()
    return _encoder


def _mentioned_metrics(query: str) -> list[str]:
    query_lower = query.lower()
    return [
        metric
        for metric, terms in _METRIC_TERMS.items()
        if any(term in query_lower for term in terms)
    ]


def _expected_complex_tools(query: str) -> tuple[list[str], list[str]]:
    expected_tools: list[str] = []
    reasons: list[str] = []
    for pattern, tools, reason in _COMPLEX_QUERY_TOOL_HINTS:
        if pattern.search(query):
            expected_tools.extend(tools)
            reasons.append(reason)
    return sorted(set(expected_tools)), reasons


def _text_blob(*parts: Any) -> str:
    return " ".join(str(part or "") for part in parts).lower()


def _validate_single_nl2sql_result(query: str, result: Any) -> tuple[bool, str]:
    """Validate that a single NL2SQL result is enough for a factual lookup."""
    if not isinstance(result, dict):
        return False, "NL2SQL did not return a structured result."

    if result.get("error"):
        return False, f"NL2SQL failed: {result['error']}"

    sql = str(result.get("sql") or "")
    columns = result.get("columns") or []
    rows = result.get("rows") or []
    evidence = _text_blob(sql, " ".join(map(str, columns)), rows[:3])

    expected_tools, reasons = _expected_complex_tools(query)
    if expected_tools:
        return (
            False,
            "Query asks for "
            + ", ".join(reasons)
            + f"; NL2SQL alone is insufficient. Expected one of: {', '.join(expected_tools)}.",
        )

    missing_metrics = [metric for metric in _mentioned_metrics(query) if metric not in evidence]
    if missing_metrics:
        return False, "NL2SQL result is missing requested metric(s): " + ", ".join(missing_metrics)

    query_lower = query.lower()
    if "product" in query_lower and _RANKING_TERMS.search(query) and "product_id" not in evidence:
        return False, "Product ranking query did not return or group by product_id."

    if _RANKING_TERMS.search(query) and "order by" not in sql.lower():
        return False, "Ranking query SQL does not order the results."

    if _RANKING_TERMS.search(query) and "limit" not in sql.lower():
        return False, "Ranking query SQL does not limit the result set."

    if _AGGREGATE_TERMS.search(query) and not re.search(r"\b(sum|avg|count|min|max)\s*\(", sql, re.I):
        return False, "Aggregate query SQL does not use an aggregate function."

    if "all time" in query_lower and re.search(r"\bwhere\b.+\bdate\b", sql, re.I | re.S):
        return False, "Query asks for all time, but SQL appears to restrict dates."

    if not rows:
        return True, "Validation passed; NL2SQL returned no matching rows."

    return True, "Validation passed."


_ANALYTICAL_RESULT_KEYS = frozenset({
    "daily_details", "positive_drivers", "negative_drivers", "kpis",
    "metrics_comparison", "ranked_products", "prediction_value",
    "explanation_summary", "optimized_forecast_sum", "baseline_forecast_sum",
})


def _has_analytical_payload(result: Any) -> bool:
    if not isinstance(result, dict) or result.get("error"):
        return False
    if any(key in result for key in _ANALYTICAL_RESULT_KEYS):
        return True
    rows = result.get("rows")
    return isinstance(rows, list) and len(rows) > 0


def validate_results(state: AgentState) -> dict[str, Any]:
    """Validate step results for completeness, non-emptiness, and relevance."""
    plan = state.get("execution_plan", [])
    step_results = state.get("step_results", {})
    query = state.get("user_query", "")

    notes: list[str] = []
    passed = True

    if not plan:
        return {"validation_passed": False, "validation_notes": "No execution plan was produced."}

    if len(plan) == 1 and plan[0].get("tool_id") == "nl2sql_query":
        step_id = plan[0].get("step_id")
        result = step_results.get(step_id)
        if result is None:
            return {
                "validation_passed": False,
                "validation_notes": f"Step {step_id} did not produce a result.",
            }

        nl2sql_passed, nl2sql_notes = _validate_single_nl2sql_result(query, result)
        if not nl2sql_passed:
            logger.warning(f"Single-step NL2SQL validation failed: {nl2sql_notes}")
            return {"validation_passed": False, "validation_notes": nl2sql_notes}

        logger.info(f"Single-step NL2SQL validation passed: {nl2sql_notes}")
        return {"validation_passed": True, "validation_notes": nl2sql_notes}

    planned_step_ids = [step.get("step_id") for step in plan]
    planned_tools = [step.get("tool_id", "") for step in plan]

    expected_tools, reasons = _expected_complex_tools(query)
    if expected_tools and not any(tool in expected_tools for tool in planned_tools):
        passed = False
        notes.append(
            "Execution plan may not answer the query: it asks for "
            + ", ".join(reasons)
            + f" but did not run any of: {', '.join(expected_tools)}."
        )

    executed_count = sum(1 for step_id in planned_step_ids if step_id in step_results)
    if executed_count < len(plan):
        passed = False
        notes.append(f"Incomplete execution: {executed_count}/{len(plan)} steps ran.")

    has_valid_data = False
    has_structured_lookup = False
    analytical_successes = 0
    step_errors = 0
    for step_id in planned_step_ids:
        result = step_results.get(step_id)
        if not result or result == {}:
            notes.append(f"Step {step_id} returned empty result.")
        elif "error" in result:
            step_errors += 1
            notes.append(f"Step {step_id} failed: {result['error']}")
        elif "rows" in result and len(result["rows"]) == 0:
            notes.append(f"Step {step_id} executed but found 0 records.")
        elif "rows" in result and "columns" in result:
            has_structured_lookup = True
            has_valid_data = True
        else:
            has_valid_data = True
            if _has_analytical_payload(result):
                analytical_successes += 1

    if not has_valid_data:
        passed = False
        notes.append("No valid data was produced by any step.")
    elif step_errors > 0:
        if analytical_successes > 0:
            notes.append(
                f"{step_errors} step(s) failed but {analytical_successes} analytical step(s) "
                "produced usable data — continuing with partial results."
            )
        else:
            passed = False

    if has_valid_data and query and not has_structured_lookup and analytical_successes == 0:
        summary_parts = []
        for step_id in planned_step_ids:
            result = step_results.get(step_id)
            if isinstance(result, dict) and "error" not in result:
                keys_str = " ".join(result.keys())
                summary_parts.append(f"Result {step_id} contains {keys_str}")

        results_summary = " | ".join(summary_parts)
        try:
            encoder = _get_encoder()
            query_emb = np.array(encoder.encode(query))
            res_emb = np.array(encoder.encode(results_summary))

            q_norm = np.linalg.norm(query_emb)
            r_norm = np.linalg.norm(res_emb)
            if q_norm > 0 and r_norm > 0:
                query_emb = query_emb / q_norm
                res_emb = res_emb / r_norm

                similarity = float(np.dot(query_emb, res_emb))
                logger.info(f"Validator semantic relevance score: {similarity:.3f}")

                if similarity < 0.18:
                    passed = False
                    notes.append(f"Low relevance score ({similarity:.3f}): The executed tools may not match the query.")
        except Exception as e:
            logger.warning(f"Semantic relevance validation skipped: {e}")

    final_notes = "\n".join(notes) if notes else "Validation passed."

    if not passed:
        logger.warning(f"Validation failed:\n{final_notes}")
    else:
        logger.info("Validation passed.")

    logger.info(f"--- VALIDATION RESULT ---\nPassed: {passed}\nNotes: {final_notes}\n-------------------------")

    return {
        "validation_passed": passed,
        "validation_notes": final_notes,
    }
