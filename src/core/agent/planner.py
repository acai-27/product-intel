import json
import re
import time
import queue
import threading
from typing import Any, Dict, Optional

import pandas as pd

from src.core.explainer import PredictionExplainer
from src.core.forecaster import ProductForecaster
from src.core.simulator import ScenarioSimulator
from src.core.nl2sql.dates import resolve_date, get_reference_date
from src.utils.logger import setup_logger

logger = setup_logger("planner_agent")

# --- Entity-extraction patterns used only by the legacy rule-based fallback
# (_fallback_rule_based_router / execute_route below). Kept local to this
# file rather than importing dag_planner's private _PRODUCT_ID_PATTERN, to
# avoid coupling this last-resort path to the primary pipeline's internals.
_FALLBACK_PRODUCT_ID_RE = re.compile(r"\bP\d+\b", re.I)
_FALLBACK_METRIC_RE = re.compile(
    r"\b(revenue|profit|orders?|conversion(?:\s*rate)?|retention(?:\s*rate)?)\b", re.I
)
_FALLBACK_HORIZON_RE = re.compile(r"(\d+)\s*(day|week|month)s?\b", re.I)
_FALLBACK_PCT_RE = re.compile(r"([+-]?\d+(?:\.\d+)?)\s*%")
_FALLBACK_NUM_RE = re.compile(r"([+-]?\d+(?:\.\d+)?)")
_FALLBACK_NEGATIVE_RE = re.compile(r"\b(decrease|reduce|cut|lower|drop|down)\b", re.I)
_FALLBACK_METRIC_MAP = {
    "revenue": "revenue",
    "profit": "profit",
    "order": "orders",
    "orders": "orders",
    "conversion": "conversion_rate",
    "conversion rate": "conversion_rate",
    "retention": "retention_rate",
    "retention rate": "retention_rate",
}
_FALLBACK_DRIVER_DEFAULTS = {"discount": "5%", "shipping": "20", "marketing": "10%"}

# Route classification, in explicit priority order (most specific intent
# first): a "why" question signals root-cause intent, "what-if" signals a
# scenario test, and a bare forecast request is the safest generic default.
# Using \b word-boundary regex here (not plain substring `in` checks) avoids
# false positives like "why" matching inside "highway", and scoring by
# keyword-hit count with a stated priority replaces what used to be an
# unstated, accidental if/elif ordering.
_FALLBACK_ROUTE_PATTERNS = {
    "forecast_explain_drivers": re.compile(r"\b(why|explain(?:ing|ed|s)?|driver|drivers|cause|caused|reason)\b", re.I),
    "simulate_scenario": re.compile(r"\b(what[\s-]?if|scenario|simulate|simulation)\b", re.I),
    "forecast_predict": re.compile(r"\b(forecast|predict|project|projection|trend|outlook)\b", re.I),
}
_FALLBACK_ROUTE_PRIORITY = list(_FALLBACK_ROUTE_PATTERNS.keys())


def _stream_text_and_visualizations(result: dict[str, Any], llm_client: Any):
    """Stream text synthesis and visualization events in parallel."""
    from src.core.agent.nodes.synthesizer import synthesize_response_stream
    from src.core.agent.visualization.generator import serialize_viz_event, stream_visualizations

    viz_queue: queue.Queue = queue.Queue()
    viz_done = threading.Event()

    def _run_viz() -> None:
        try:
            for event in stream_visualizations(result, llm_client):
                viz_queue.put(event)
        finally:
            viz_done.set()

    threading.Thread(target=_run_viz, daemon=True).start()

    def _drain_viz() -> list[str]:
        drained: list[str] = []
        while True:
            try:
                drained.append(serialize_viz_event(viz_queue.get_nowait()))
            except queue.Empty:
                break
        return drained

    for chunk in synthesize_response_stream(result, llm_client):
        yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"
        for payload in _drain_viz():
            yield payload

    while not viz_done.is_set() or not viz_queue.empty():
        for payload in _drain_viz():
            yield payload
        if viz_done.is_set() and viz_queue.empty():
            break
        time.sleep(0.05)


class LLMPlannerAgent:
    """Compatibility wrapper for the SSE agent endpoint.

    The final architecture uses the LangGraph pipeline as the orchestrator.
    This class remains only because `src.api.routers.agent` depends on an
    object with `process_query_stream()`.
    """

    def __init__(
        self,
        forecaster: ProductForecaster,
        explainer: PredictionExplainer,
        simulator: ScenarioSimulator,
        df_historical: Optional[pd.DataFrame] = None,
    ):
        self.forecaster = forecaster
        self.explainer = explainer
        self.simulator = simulator
        self.df_historical = df_historical

        from src.core.llm import get_llm_client
        self.llm_client = get_llm_client()

    def process_query_stream(self, query: str):
        """Run the query through LangGraph and stream Server-Sent Events."""
        try:
            from src.core.agent.graph import _compiled_graph, _llm_client
            from src.core.agent.state import AgentState

            if _compiled_graph is not None:
                initial_state: AgentState = {
                    "user_query": query,
                    "intent": "",
                    "intent_confidence": 0.0,
                    "extracted_params": {},
                    "is_blocked": False,
                    "block_reason": "",
                    "dag_source": "",
                    "execution_plan": [],
                    "current_step_index": 0,
                    "step_results": {},
                    "execution_errors": [],
                    "validation_passed": True,
                    "validation_notes": "",
                    "retry_count": 0,
                    "final_response": "",
                    "raw_data": {},
                    "route_called": "",
                }

                result = initial_state
                yield f"data: {json.dumps({'type': 'status', 'content': 'Classifying query intent...'})}\n\n"

                for event in _compiled_graph.stream(initial_state):
                    for node_name, state_update in event.items():
                        result = {**result, **state_update}

                        if node_name == "intent_classifier":
                            intent = result.get("intent", "analytical")
                            conf = result.get("intent_confidence", 1.0)
                            yield f"data: {json.dumps({'type': 'status', 'content': f'Classified intent: {intent} ({conf*100:.0f}% confidence)'})}\n\n"
                        elif node_name == "dag_planner":
                            plan = result.get("execution_plan", [])
                            tool_ids = [
                                s.get("tool_id", s.get("step_id", "?"))
                                for s in plan
                                if isinstance(s, dict)
                            ]
                            plan_str = f" ({', '.join(tool_ids)})" if tool_ids else ""
                            yield f"data: {json.dumps({'type': 'status', 'content': f'Formulating computation plan{plan_str}...'})}\n\n"
                        elif node_name == "dag_executor":
                            steps = result.get("execution_plan", [])
                            idx = result.get("current_step_index", 0)
                            step = steps[idx] if steps and idx < len(steps) else {}
                            step_label = step.get("tool_id", step.get("step_id", "")) if isinstance(step, dict) else str(step)
                            step_info = f" (Step {idx + 1}/{len(steps)}: {step_label})" if step_label else ""
                            yield f"data: {json.dumps({'type': 'status', 'content': f'Running deterministic calculations{step_info}...'})}\n\n"
                        elif node_name == "validator":
                            passed = result.get("validation_passed", True)
                            status_text = "passed" if passed else "flagged inconsistencies"
                            yield f"data: {json.dumps({'type': 'status', 'content': f'Validating output... validation {status_text}.'})}\n\n"
                        elif node_name == "replanner":
                            yield f"data: {json.dumps({'type': 'status', 'content': 'Adjusting parameters for refinement...'})}\n\n"
                        elif node_name == "fast_response":
                            yield f"data: {json.dumps({'type': 'status', 'content': 'Generating fast summary...'})}\n\n"

                meta_chunk = {
                    "type": "metadata",
                    "query": result.get("user_query", query),
                    "route_called": result.get("route_called", ""),
                    "raw_data": result.get("raw_data", {}),
                }
                yield f"data: {json.dumps(meta_chunk)}\n\n"
                yield from _stream_text_and_visualizations(result, _llm_client)
                yield "data: [DONE]\n\n"
                return

        except Exception as e:
            logger.warning(f"LangGraph pipeline failed, using minimal fallback: {e}")

        fallback = self._fallback_rule_based_router(query)
        route = fallback.get("route", "forecast_predict")
        raw_data = self.execute_route(route, fallback.get("params", {}))
        state = {
            "user_query": query,
            "intent": "analytical",
            "route_called": route,
            "raw_data": {"s1": raw_data},
            "execution_plan": [{"step_id": "s1", "tool_id": route, "params": fallback.get("params", {}), "depends_on": []}],
        }
        yield f"data: {json.dumps({'type': 'metadata', 'query': query, 'route_called': route, 'raw_data': raw_data})}\n\n"
        yield from _stream_text_and_visualizations(state, self.llm_client)
        yield "data: [DONE]\n\n"

    def execute_route(self, route: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Minimal legacy fallback covering only final-scope engines."""
        from src.api.dependencies import get_historical_df_from_db

        product_id = params.get("product_id", "P001")
        df_hist = get_historical_df_from_db(product_id=product_id)

        try:
            if route == "forecast_predict":
                horizon = int(params.get("horizon_days", 30))
                forecast_df = self.forecaster.forecast(df_hist, product_id, horizon)
                records = [
                    {
                        "date": row["date"].strftime("%Y-%m-%d"),
                        "revenue": round(float(row["revenue"]), 2),
                        "profit": round(float(row["profit"]), 2),
                        "orders": round(float(row["orders"]), 2),
                    }
                    for _, row in forecast_df.head(10).iterrows()
                ]
                return {
                    "product_id": product_id,
                    "horizon_days": horizon,
                    "forecast_total_revenue": round(float(forecast_df["revenue"].sum()), 2),
                    "forecast_total_profit": round(float(forecast_df["profit"].sum()), 2),
                    "forecast_total_orders": round(float(forecast_df["orders"].sum()), 2),
                    "daily_details": records,
                }

            if route == "forecast_explain_drivers":
                return self.explainer.explain_prediction(
                    historical_df=df_hist,
                    product_id=product_id,
                    target_metric=params.get("target_metric", "revenue"),
                    date=params.get("date", "2025-01-05"),
                )

            if route == "simulate_scenario":
                changes = params.get("changes") or ["discount +5%"]
                return self.simulator.evaluate_scenario(
                    historical_df=df_hist,
                    product_id=product_id,
                    horizon_days=int(params.get("horizon_days", 30)),
                    changes=changes,
                )

            raise ValueError(f"Unsupported fallback route: {route}")
        except Exception as e:
            logger.error(f"Fallback execution failed for route {route}: {e}")
            return {"error": str(e)}

    def _extract_magnitude_near(self, q: str, driver: str, as_percent: bool) -> str:
        """
        Look for a signed/unsigned number near the driver keyword (e.g. finds
        "15" in "increase discount by 15%") and infer direction from nearby
        words. Falls back to the same fixed defaults the old hardcoded
        version used, so behavior degrades gracefully rather than guessing
        wildly when no number is present.
        """
        idx = q.find(driver)
        window = q[max(0, idx - 25): idx + 35]

        match = _FALLBACK_PCT_RE.search(window) or _FALLBACK_NUM_RE.search(window)
        magnitude = _FALLBACK_DRIVER_DEFAULTS.get(driver, "5%")
        if match:
            raw = match.group(1).lstrip("+-")
            magnitude = f"{raw}%" if as_percent else raw

        sign = "-" if _FALLBACK_NEGATIVE_RE.search(window) else "+"
        return f"{sign}{magnitude}"

    def _classify_fallback_route(self, q: str) -> str:
        """
        Score each route by regex keyword-hit count, in the explicit
        priority order defined by _FALLBACK_ROUTE_PATTERNS (explain > 
        simulate > predict). Replaces what used to be two sequential
        if-checks, which resolved conflicting keywords (e.g. a query
        containing both "why" and "simulate") via accidental code
        ordering rather than a stated rule.
        """
        scores = {route: len(pattern.findall(q)) for route, pattern in _FALLBACK_ROUTE_PATTERNS.items()}
        best_route = max(scores, key=lambda r: (scores[r], -_FALLBACK_ROUTE_PRIORITY.index(r)))
        if scores[best_route] == 0:
            return "forecast_predict"  # no keyword signal at all -> safest, most generic default
        return best_route

    def _fallback_rule_based_router(self, query: str) -> Dict[str, Any]:
        """
        Small deterministic fallback limited to the final engines.

        Unlike the earlier version, this extracts real entities from the
        query (product_id, metric, horizon, date, change magnitude) instead
        of hardcoding "P001" / "revenue" / a fixed date for every request,
        and classifies the route via regex keyword scoring with an explicit
        priority instead of sequential if-checks. It is still only used
        when the primary LangGraph pipeline fails to even initialize --
        normal per-query failures go through the validator/replanner loop,
        not this path.
        """
        q = query.lower()

        product_match = _FALLBACK_PRODUCT_ID_RE.search(query)
        product_id = product_match.group(0).upper() if product_match else "P001"

        metric_match = _FALLBACK_METRIC_RE.search(q)
        metric_raw = metric_match.group(1).strip() if metric_match else "revenue"
        target_metric = _FALLBACK_METRIC_MAP.get(metric_raw, "revenue")

        horizon_match = _FALLBACK_HORIZON_RE.search(q)
        if horizon_match:
            amount, unit = int(horizon_match.group(1)), horizon_match.group(2)
            horizon_days = amount * {"day": 1, "week": 7, "month": 30}[unit]
        else:
            horizon_days = 30
        horizon_days = max(1, min(horizon_days, 90))  # keep within a sane, supported range

        # Anchor to the dataset's actual latest date rather than a hardcoded
        # string that may not even fall inside the current data's range.
        reference_date = get_reference_date()
        resolved = resolve_date(query, reference=reference_date) or reference_date
        date_str = resolved.strftime("%Y-%m-%d")

        route = self._classify_fallback_route(q)

        if route == "simulate_scenario":
            changes = []
            if "discount" in q:
                changes.append(f"discount {self._extract_magnitude_near(q, 'discount', as_percent=True)}")
            if "shipping" in q:
                changes.append(f"shipping {self._extract_magnitude_near(q, 'shipping', as_percent=False)}")
            if "marketing" in q:
                changes.append(f"marketing {self._extract_magnitude_near(q, 'marketing', as_percent=True)}")
            return {
                "route": "simulate_scenario",
                "params": {"product_id": product_id, "changes": changes or ["discount +5%"], "horizon_days": horizon_days},
            }

        if route == "forecast_explain_drivers":
            return {
                "route": "forecast_explain_drivers",
                "params": {"product_id": product_id, "target_metric": target_metric, "date": date_str},
            }

        return {"route": "forecast_predict", "params": {"product_id": product_id, "horizon_days": horizon_days}}