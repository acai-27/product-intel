"""
LangGraph StateGraph — compiles and runs the agent pipeline.

Flow:
Intent Classifier → (Fast Response | DAG Planner | DAG Executor)
DAG Planner → DAG Executor
DAG Executor → Validator
Validator → (END | Replanner) — synthesis runs in the API stream layer after the graph completes.
Replanner → DAG Executor
"""

from typing import Any

# pyrefly: ignore [missing-import]
from langgraph.graph import StateGraph, END

from src.core.agent.state import AgentState
from src.core.agent.nodes.intent_classifier import classify_intent, is_non_analytical
from src.core.agent.nodes.dag_planner import plan_dag
from src.core.agent.nodes.dag_executor import execute_dag
from src.core.agent.nodes.validator import validate_results
from src.core.agent.nodes.replanner import replan_dag
from src.core.agent.nodes.synthesizer import synthesize_fast_response
from src.core.llm import LLMClient
from src.utils.logger import setup_logger

logger = setup_logger("agent_graph")

# Module-level cache for compiled graph
_compiled_graph = None
_llm_client: LLMClient | None = None
_engines: dict[str, Any] = {}


def init_graph(llm_client: LLMClient, engines: dict[str, Any]) -> None:
    """Initialize the graph with shared resources. Called once at startup."""
    global _compiled_graph, _llm_client, _engines
    _llm_client = llm_client
    _engines = engines
    _compiled_graph = _build_graph()
    logger.info("LangGraph agent pipeline compiled successfully.")


def _build_graph() -> Any:
    """Build and compile the LangGraph StateGraph."""
    graph = StateGraph(AgentState)

    # ── Register nodes ───────────────────────────────────────────────
    graph.add_node("intent_classifier", _node_classify_intent)
    graph.add_node("fast_response", _node_fast_response)
    graph.add_node("dag_planner", _node_plan_dag)
    graph.add_node("dag_executor", _node_execute_dag)
    graph.add_node("validator", _node_validate)
    graph.add_node("replanner", _node_replan)

    # ── Set entry point ──────────────────────────────────────────────
    graph.set_entry_point("intent_classifier")

    # ── Conditional routing from intent classifier ───────────────────
    graph.add_conditional_edges(
        "intent_classifier",
        _route_after_classification,
        {
            "fast_response": "fast_response",
            "dag_executor": "dag_executor",
            "dag_planner": "dag_planner",
        },
    )

    # ── Linear edges ─────────────────────────────────────────────────
    graph.add_edge("fast_response", END)
    graph.add_conditional_edges(
        "dag_planner",
        _route_after_planning,
        {
            "end": END,
            "dag_executor": "dag_executor",
        },
    )
    graph.add_edge("dag_executor", "validator")

    # ── Conditional routing from validator ───────────────────────────
    graph.add_conditional_edges(
        "validator",
        _route_after_validation,
        {
            "end": END,
            "replanner": "replanner",
        },
    )

    graph.add_conditional_edges(
        "replanner",
        _route_after_replan,
        {
            "end": END,
            "dag_executor": "dag_executor",
        },
    )

    return graph.compile()


# ── Node wrappers (close over module-level client/engines) ───────────────


def _node_classify_intent(state: AgentState) -> dict[str, Any]:
    """Node wrapper for intent classification."""
    return classify_intent(state, _llm_client)


def _node_fast_response(state: AgentState) -> dict[str, Any]:
    """Node wrapper for fast non-analytical responses."""
    return synthesize_fast_response(state, _llm_client)


def _node_plan_dag(state: AgentState) -> dict[str, Any]:
    """Node wrapper for DAG planning."""
    # Pass model_tier capable for DAG planner
    return plan_dag(state, _llm_client)


def _node_execute_dag(state: AgentState) -> dict[str, Any]:
    """Node wrapper for DAG execution."""
    return execute_dag(state, _engines)


def _node_validate(state: AgentState) -> dict[str, Any]:
    """Node wrapper for result validation."""
    return validate_results(state)


def _node_replan(state: AgentState) -> dict[str, Any]:
    """Node wrapper for DAG re-planning."""
    return replan_dag(state, _llm_client)


# ── Routing functions ────────────────────────────────────────────────────


def _route_after_classification(state: AgentState) -> str:
    """Route to fast_response, dag_planner, or directly to dag_executor."""
    if is_non_analytical(state):
        return "fast_response"
    if state["intent"] == "data_lookup" and "execution_plan" in state:
        return "dag_executor"
    return "dag_planner"


def _route_after_planning(state: AgentState) -> str:
    """End early when planning produced a clarification response."""
    if state.get("final_response"):
        return "end"
    return "dag_executor"


def _route_after_validation(state: AgentState) -> str:
    """Route to END or replanner based on validation results."""
    if state.get("validation_passed", True):
        return "end"
    return "replanner"


def _route_after_replan(state: AgentState) -> str:
    """Route to executor only when the replanner produced a retry plan."""
    if state.get("validation_passed", False):
        return "end"
    return "dag_executor"


# ── Public API ───────────────────────────────────────────────────────────


def run_agent_graph(query: str) -> dict[str, Any]:
    """Run a user query through the full LangGraph pipeline."""
    if _compiled_graph is None:
        raise RuntimeError("Agent graph not initialized. Call init_graph() first.")

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

    result = _compiled_graph.invoke(initial_state)
    return result
