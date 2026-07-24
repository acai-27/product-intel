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
from src.utils.logger import setup_logger

logger = setup_logger("planner_agent")
# --- Define these at the very top of the file, outside any class ---
_PRODUCT_ID_PATTERN = re.compile(r"\b[pP]\d{3,4}\b")
_DATE_LITERAL = re.compile(r"(\d{4}-\d{2}-\d{2})")

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

    def _fallback_rule_based_router(self, query: str) -> Dict[str, Any]:
        """Small deterministic fallback limited to the final engines."""
        q = query.lower()
        # Dynamically extract entities while preserving the original defaults
        product_match = _PRODUCT_ID_PATTERN.search(query)
        product_id = product_match.group(0).upper() if product_match else "P001"

        date_match = _DATE_LITERAL.search(query)
        date_val = date_match.group(1) if date_match else "2025-01-05"

        if "what if" in q or "what-if" in q or "scenario" in q or "simulate" in q:
            changes = []
            if "discount" in q:
                changes.append("discount +5%")
            if "shipping" in q:
                changes.append("shipping +20")
            if "marketing" in q:
                changes.append("marketing +10%")
            return {
                "route": "simulate_scenario", 
                "params": {
                    "product_id": product_id, 
                    "changes": changes or ["discount +5%"], 
                    "horizon_days": 30
                }
            }
            
        if "why" in q or "explain" in q or "driver" in q:
            return {
                "route": "forecast_explain_drivers", 
                "params": {
                    "product_id": product_id, 
                    "target_metric": "revenue", 
                    "date": date_val
                }
            }
            
        return {
            "route": "forecast_predict", 
            "params": {
                "product_id": product_id, 
                "horizon_days": 30
            }
        }