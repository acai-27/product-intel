"""
Replanner Node — contextual re-planning after a validation failure.

Uses a fast deterministic patch for common wiring failures before falling
back to a compact LLM replan.
"""

from __future__ import annotations

import json
import re
from typing import Any

from src.core.agent.state import AgentState
from src.core.agent.nodes.dag_planner import normalize_dag
from src.core.agent.registry.capability_registry import CAPABILITY_REGISTRY
from src.core.llm import LLMClient
from src.utils.logger import setup_logger

logger = setup_logger("replanner")

_WIRING_FAILURE = re.compile(
    r"Could not resolve input_from|Missing required parameters",
    re.I,
)

_REPLANNER_SYSTEM_PROMPT = """\
You are the DAG Replanner. A previous execution plan failed.
Generate a corrected minimal DAG.

Original Query: "{query}"
Failure: {notes}

Failed plan:
{previous_dag}

Rules:
- Fix only what failed. Keep successful tool choices when possible.
- Put explicit product_id/date from the user query directly in params — do NOT wire date from NL2SQL unless that step SELECTs date.
- For forecast_explain_drivers after forecast_predict, wire date from the forecast step or put the latest data date in params.
- Never invent placeholder values.

Output ONLY JSON:
{{
  "reasoning": "...",
  "dag": [{{"step_id": "s1", "tool_id": "...", "params": {{}}, "input_from": {{}}, "depends_on": []}}]
}}
"""


def _compact_tool_list() -> str:
    lines: list[str] = []
    for tool_id, spec in CAPABILITY_REGISTRY.items():
        schema = spec.get("input_schema", {})
        required = [k for k, v in schema.items() if v.get("required")]
        lines.append(f"- {tool_id}: {spec.get('description', '')[:120]} | required: {required}")
    return "\n".join(lines)


def try_deterministic_replan(state: AgentState) -> dict[str, Any] | None:
    """Patch common wiring failures without calling the LLM."""
    notes = state.get("validation_notes", "")
    if not _WIRING_FAILURE.search(notes):
        return None

    query = state.get("user_query", "")
    previous_plan = state.get("execution_plan", [])
    if not previous_plan:
        return None

    fixed_plan = normalize_dag(previous_plan, query, state.get("extracted_params"))
    if fixed_plan == previous_plan:
        return None

    logger.info("Deterministic replanner patched DAG without LLM.")
    return {
        "execution_plan": fixed_plan,
        "dag_source": "deterministic_retry",
        "retry_count": state.get("retry_count", 0) + 1,
        "validation_passed": False,
    }


def replan_dag(state: AgentState, llm_client: LLMClient) -> dict[str, Any]:
    """Generate a corrected DAG after validation failure."""
    retry_count = state.get("retry_count", 0)

    if retry_count >= 1:
        logger.warning("Max retries reached. Forcing pass to synthesizer.")
        return {
            "validation_passed": True,
            "validation_notes": state.get("validation_notes", "") + "\nMax retries reached.",
        }

    logger.info("Validation failed. Initiating Replanner.")

    deterministic = try_deterministic_replan(state)
    if deterministic:
        logger.info(f"Patched plan:\n{json.dumps(deterministic['execution_plan'], indent=2)}")
        return deterministic

    query = state.get("user_query", "")
    notes = state.get("validation_notes", "")
    previous_dag = json.dumps(state.get("execution_plan", []), indent=2)

    system_prompt = _REPLANNER_SYSTEM_PROMPT.format(
        query=query,
        notes=notes,
        previous_dag=previous_dag,
    )

    try:
        result = llm_client.generate_json(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate the corrected DAG."},
            ],
            temperature=0.1,
            max_tokens=600,
            model_tier="fast",
        )
        new_dag = normalize_dag(
            result.get("dag", []),
            query,
            state.get("extracted_params"),
        )
        reasoning = result.get("reasoning", "")
        logger.info(f"Replanner generated new DAG with {len(new_dag)} steps.")
        logger.info(f"Replanner Reasoning: {reasoning}")

        return {
            "execution_plan": new_dag,
            "dag_source": "dynamic_retry",
            "retry_count": retry_count + 1,
            "validation_passed": False,
        }

    except Exception as e:
        logger.error(f"Replanner failed: {e}. Forcing pass to synthesizer.")
        return {
            "validation_passed": True,
            "validation_notes": notes + f"\nReplanner failed to generate fallback: {e}",
        }
