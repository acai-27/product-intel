"""
Synthesizer Node — streams natural language reports for every response type.

All user-facing text (greetings, guardrails, NL2SQL, analytical) is streamed.
"""

import json
from typing import Any, Iterator

from src.core.agent.state import AgentState
from src.core.agent.registry.capability_registry import get_tool_descriptions_for_prompt
from src.core.agent.registry.data_registry import get_data_summary_for_prompt
from src.core.llm import LLMClient
from src.utils.logger import setup_logger

logger = setup_logger("synthesizer")

_SYNTHESIS_SYSTEM_PROMPT = """\
You are a professional Business Intelligence Assistant.
The user asked a question. An analytics engine ran calculations and produced raw JSON data.
Summarize the results clearly in natural language using professional markdown.
Highlight the most critical business insights and recommendations.
Do not reference internal technical details like step IDs (e.g. 's1', 's2') or raw JSON keys.
Speak directly to the business user."""

_NL2SQL_SYNTHESIS_PROMPT = """\
You are a professional Business Intelligence Assistant.
The user asked a factual data question. A database query was executed and returned tabular results.
Write a clear, user-friendly markdown answer that highlights the key numbers and findings.
Use bullet points or a short table when helpful. Do not mention SQL, step IDs, or internal systems.
If no rows were returned, explain that plainly and suggest how the user might refine the question."""

_FAST_INTENT_COPY: dict[str, str] = {
    "greeting": (
        "Hello! I'm your AI-powered Business Analytics Assistant. "
        "I can help you with forecasting, trend analysis, anomaly detection, "
        "what-if simulations, and product data lookup. How can I assist you today?"
    ),
    "system_status": (
        "The system is online and healthy. All analytics engines — forecasting, anomaly detection, "
        "scenario simulation, forecast explanation, and NL2SQL — are operational."
    ),
    "guardrail_block": (
        "I'm sorry, but I can only help with business analytics questions. "
        "Try asking about forecasts, explanations, simulations, anomalies, or product data lookup."
    ),
    "clarification": (
        "Could you please provide more details? For example, you can ask me to "
        "forecast revenue, explain why a metric changed, simulate a what-if scenario, "
        "scan for anomalies, or query product performance data."
    ),
}


def synthesize_fast_response(state: AgentState, llm_client: LLMClient) -> dict[str, Any]:
    """Set routing metadata for fast intents; text is streamed later in the API layer."""
    intent = state["intent"]
    route = intent
    if state.get("is_blocked"):
        route = "guardrail_block"
    elif intent == "clarification_needed":
        route = "clarification"

    payload: dict[str, Any] = {
        "final_response": "",
        "raw_data": {},
        "route_called": route,
    }

    if intent == "meta_query":
        payload["raw_data"] = {
            "tools_str": get_tool_descriptions_for_prompt(),
            "data_str": get_data_summary_for_prompt(),
        }
        payload["route_called"] = "meta_query"
    elif intent == "system_status":
        payload["raw_data"] = {"status": "healthy"}

    return payload


def synthesize_response_stream(
    state: AgentState,
    llm_client: LLMClient,
) -> Iterator[str]:
    """Unified streaming entry for every post-graph response."""
    intent = state.get("intent", "")
    route = state.get("route_called", "") or intent
    final_response = (state.get("final_response") or "").strip()

    if final_response:
        yield from _stream_text(final_response)
        return

    if route in _FAST_INTENT_COPY or intent in _FAST_INTENT_COPY:
        key = route if route in _FAST_INTENT_COPY else intent
        yield from _stream_text(_FAST_INTENT_COPY[key])
        return

    yield from synthesize_analytical_response_stream(state, llm_client)


def synthesize_analytical_response_stream(
    state: AgentState,
    llm_client: LLMClient,
) -> Iterator[str]:
    """Stream analytical synthesis from DAG step results."""
    raw_data = state.get("raw_data", {})
    route = state.get("route_called", "")
    notes = state.get("validation_notes", "")

    if route == "nl2sql_query":
        step_id = state.get("execution_plan", [{}])[0].get("step_id")
        step_data = raw_data.get(step_id, raw_data) if step_id else raw_data
        yield from _stream_nl2sql_synthesis(state.get("user_query", ""), step_data, notes, llm_client)
        return

    if route == "meta_query":
        yield from _stream_meta_query(state, llm_client)
        return

    try:
        truncated = json.dumps(raw_data, indent=2, default=str)[:4000]
        user_msg = f'User Query: "{state["user_query"]}"\n'
        if notes and "passed" not in notes.lower():
            user_msg += f'Validation Context (mention if relevant): "{notes}"\n'
        user_msg += f"Raw Data Results:\n{truncated}"

        yield from llm_client.generate_stream(
            messages=[
                {"role": "system", "content": _SYNTHESIS_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
            max_tokens=800,
            model_tier="fast",
        )
    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        yield (
            f"Analysis completed. Here are the raw results:\n\n"
            f"{json.dumps(raw_data, indent=2, default=str)[:2000]}"
        )


def _stream_nl2sql_synthesis(
    question: str,
    step_data: dict[str, Any],
    notes: str,
    llm_client: LLMClient,
) -> Iterator[str]:
    if not isinstance(step_data, dict):
        yield "I couldn't retrieve that from the database."
        return

    if step_data.get("error"):
        yield (
            "I couldn't retrieve that from the database. "
            f"Reason: {step_data['error']}\n\n"
            "Try rephrasing, or specify a product (e.g. P001) and a date range."
        )
        return

    context = json.dumps(step_data, indent=2, default=str)[:3500]
    user_msg = (
        f'User Question: "{question}"\n\n'
        f"Database Results:\n{context}"
    )
    if notes and "passed" not in notes.lower():
        user_msg += f"\n\nValidation note: {notes}"

    try:
        yield from llm_client.generate_stream(
            messages=[
                {"role": "system", "content": _NL2SQL_SYNTHESIS_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.25,
            max_tokens=600,
            model_tier="fast",
        )
    except Exception as e:
        logger.error(f"NL2SQL synthesis failed: {e}")
        fallback = _format_nl2sql_table(question, step_data)
        yield fallback or "No matching records were found for that query."


def _stream_meta_query(state: AgentState, llm_client: LLMClient) -> Iterator[str]:
    query = state.get("user_query", "What can you do?")
    raw_data = state.get("raw_data", {})
    tools_str = raw_data.get("tools_str") or get_tool_descriptions_for_prompt()
    data_str = raw_data.get("data_str") or get_data_summary_for_prompt()
    system_msg = (
        "You are a helpful Business Intelligence AI. The user is asking about your capabilities or data access. "
        f"Capabilities:\n\n{tools_str}\n\nData context:\n\n{data_str}\n\n"
        "Answer concisely and professionally based ONLY on this context."
    )
    try:
        yield from llm_client.generate_stream(
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": query},
            ],
            temperature=0.2,
            max_tokens=600,
            model_tier="fast",
        )
    except Exception as e:
        logger.error(f"Meta query synthesis failed: {e}")
        yield from _stream_text(
            "You can ask me to forecast revenue, explain metric drops, simulate business scenarios, "
            "detect anomalies, or query product performance data."
        )


def _stream_text(text: str, chunk_size: int = 16) -> Iterator[str]:
    """Yield text in chunks so the UI shows progressive streaming."""
    if not text:
        return
    for i in range(0, len(text), chunk_size):
        yield text[i:i + chunk_size]


def _format_nl2sql_table(question: str, raw_data: dict[str, Any]) -> str | None:
    rows = raw_data.get("rows", [])
    if not rows:
        return None

    columns = raw_data.get("columns") or list(rows[0].keys())
    lines: list[str] = []
    if question:
        lines.append(f"Results for: _{question.strip()}_\n")
    lines.append("| " + " | ".join(str(c) for c in columns) + " |")
    lines.append("| " + " | ".join("---" for _ in columns) + " |")
    for row in rows:
        cells = []
        for col in columns:
            val = row.get(col)
            if val is None:
                cells.append("—")
            elif isinstance(val, float):
                cells.append(f"{val:,.2f}")
            elif isinstance(val, int):
                cells.append(f"{val:,}")
            else:
                cells.append(str(val))
        lines.append("| " + " | ".join(cells) + " |")
    lines.append(f"\n**{len(rows)} row(s) returned.**")
    return "\n".join(lines)
