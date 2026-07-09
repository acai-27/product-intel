"""
DAG Planner Node — generates dynamic execution plans via LLM.

Receives the capability registry, data registry, and temporal context,
then normalizes the plan with discovery injection and safe dependency wiring.
"""

from typing import TYPE_CHECKING, Any
import json
import re

from src.core.agent.state import AgentState
from src.core.agent.prompts.planner_prompt import build_planner_system_prompt
from src.core.agent.registry.capability_registry import CAPABILITY_REGISTRY, get_tool_descriptions_for_prompt
from src.core.agent.registry.data_registry import get_data_summary_for_prompt
from src.core.nl2sql.dates import get_date_context_for_prompt
from src.utils.logger import setup_logger

if TYPE_CHECKING:
    from src.core.llm import LLMClient

logger = setup_logger("dag_planner")

_PLACEHOLDER_VALUES = {"P001", "2025-01-05"}
_DISCOVERABLE_FIELDS = {"product_id", "date", "target_date", "category"}
_PRODUCT_ID_PATTERN = re.compile(r"\bP\d+\b", re.I)
_DATE_LITERAL = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_DISCOVERY_QUERY = re.compile(
    r"\b(find|identify|which|largest|smallest|top|rank|return|discover|biggest|worst|best|drop)\b",
    re.I,
)
_TEMPORAL_TERMS = (
    "date", "day", "week", "month", "year", "today", "yesterday", "when",
    "drop", "spike", "last week", "this week",
)


def plan_dag(state: AgentState, llm_client: "LLMClient") -> dict[str, Any]:
    """Generate a dynamic execution DAG using the LLM planner."""
    extracted_params = state.get("extracted_params", {})
    query = state.get("user_query", "") or extracted_params.get("query", "")
    logger.info("Generating dynamic DAG via LLM.")
    return _plan_dag_with_llm(state, llm_client, query, extracted_params)


def _plan_dag_with_llm(
    state: AgentState,
    llm_client: "LLMClient",
    query: str,
    extracted_params: dict[str, Any],
) -> dict[str, Any]:
    tool_desc = get_tool_descriptions_for_prompt()
    data_desc = get_data_summary_for_prompt()
    temporal_context = get_date_context_for_prompt()
    params_json = json.dumps(extracted_params)

    system_prompt = build_planner_system_prompt(
        tool_descriptions=tool_desc,
        data_summary=data_desc,
        temporal_context=temporal_context,
        params_json=params_json,
    )

    try:
        result = llm_client.generate_json(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            temperature=0.1,
            max_tokens=1000,
        )
        return _build_plan_response(result, query, "dynamic", extracted_params)

    except Exception as e:
        logger.error(f"Dynamic DAG generation failed: {e}. Retrying once...")
        try:
            error_feedback = (
                f"Your previous attempt failed with error: {e}. "
                "Please ensure you output ONLY valid JSON matching the requested schema."
            )
            result = llm_client.generate_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                    {"role": "user", "content": error_feedback},
                ],
                temperature=0.1,
                max_tokens=1000,
            )
            return _build_plan_response(result, query, "dynamic_retry", extracted_params)

        except Exception as retry_e:
            logger.error(f"Dynamic DAG retry also failed: {retry_e}. Using NL2SQL fallback.")
            return {
                "dag_source": "dynamic_fallback",
                "execution_plan": normalize_dag([
                    {
                        "step_id": "s1",
                        "tool_id": "nl2sql_query",
                        "params": {"query": query},
                        "input_from": {},
                        "depends_on": [],
                    }
                ], query, extracted_params),
            }


def _build_plan_response(
    result: dict[str, Any],
    query: str,
    source: str,
    extracted_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    dag = normalize_dag(result.get("dag", []), query, extracted_params)
    clarification = result.get("clarification", "")
    reasoning = result.get("reasoning", "")
    logger.info(f"DAG ({source}) with {len(dag)} steps. Reasoning: {reasoning}")

    if not dag:
        return {
            "dag_source": f"{source}_clarification",
            "execution_plan": [],
            "final_response": clarification or (
                "I need one more detail to run this analysis. "
                "Which product, date range, or metric should I use?"
            ),
            "route_called": "clarification",
        }

    return {"dag_source": source, "execution_plan": dag}


def extract_query_entities(
    query: str,
    extracted_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Pull product_id and date literals the user explicitly mentioned."""
    from src.core.nl2sql.dates import resolve_date

    entities: dict[str, Any] = {}
    if extracted_params:
        for key in ("product_id", "date", "target_date", "target_metric", "category"):
            val = extracted_params.get(key)
            if val not in (None, ""):
                entities[key] = val

    product_match = _PRODUCT_ID_PATTERN.search(query)
    if product_match:
        entities["product_id"] = product_match.group(0).upper()

    date_match = _DATE_LITERAL.search(query)
    if date_match:
        entities["date"] = date_match.group(1)
    else:
        on_date = re.search(
            r"\bon\s+(\d{4}-\d{2}-\d{2}|\w+\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?)\b",
            query,
            re.I,
        )
        if on_date:
            parsed = resolve_date(on_date.group(1))
            if parsed is not None:
                entities["date"] = parsed.strftime("%Y-%m-%d")

    if "date" in entities and "target_date" not in entities:
        entities["target_date"] = entities["date"]

    return entities


def normalize_dag(
    dag: Any,
    query: str,
    extracted_params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Make common LLM / template planning mistakes safer before execution."""
    if not isinstance(dag, list):
        return []

    entities = extract_query_entities(query, extracted_params)
    normalized = _normalize_steps(dag, query, entities)
    normalized = _inject_discovery_steps(normalized, query, entities)
    normalized = _sanitize_input_from(normalized, query)
    normalized = _apply_query_entities(normalized, query, entities)
    return _fill_required_params(normalized, query, entities)


def _apply_query_entities(
    dag: list[dict[str, Any]],
    query: str,
    entities: dict[str, Any],
) -> list[dict[str, Any]]:
    """Prefer explicit user-provided product_id/date over NL2SQL wiring."""
    if not dag or not entities:
        return dag

    query_lower = query.lower()
    updated: list[dict[str, Any]] = []

    for step in dag:
        step_copy = dict(step)
        tool_id = step_copy.get("tool_id", "")
        schema = CAPABILITY_REGISTRY.get(tool_id, {}).get("input_schema", {})
        params = dict(step_copy.get("params") or {})
        input_from = dict(step_copy.get("input_from") or {})
        depends_on = list(step_copy.get("depends_on") or [])

        for field, value in entities.items():
            if field not in schema or value in (None, ""):
                continue

            alias_fields = ("date", "target_date") if field in ("date", "target_date") else (field,)
            for alias in alias_fields:
                if alias not in schema:
                    continue

                value_text = str(value)
                user_supplied = False
                if field == "product_id":
                    user_supplied = _query_explicitly_targets_product(query, value_text)
                elif field in ("date", "target_date"):
                    user_supplied = (
                        value_text.lower() in query_lower or _DATE_LITERAL.search(query) is not None
                    )
                if not user_supplied:
                    continue

                if alias in ("date", "target_date"):
                    from src.core.nl2sql.dates import resolve_date
                    parsed = resolve_date(value_text)
                    if parsed is not None:
                        value_text = parsed.strftime("%Y-%m-%d")

                params[alias] = value_text
                if alias in input_from:
                    src = input_from.pop(alias)
                    src_step = src.get("step") if isinstance(src, dict) else str(src).split(".", 1)[0]
                    if src_step in depends_on and not any(
                        input_from.get(k, {}).get("step") == src_step
                        if isinstance(input_from.get(k), dict)
                        else str(input_from.get(k, "")).startswith(f"{src_step}.")
                        for k in input_from
                    ):
                        depends_on = [d for d in depends_on if d != src_step]

        step_copy["params"] = params
        step_copy["input_from"] = input_from
        step_copy["depends_on"] = depends_on
        updated.append(step_copy)

    return updated


def normalize_dag_legacy(dag: Any, query: str) -> list[dict[str, Any]]:
    return normalize_dag(dag, query, None)


# Backward-compatible alias for tests
_normalize_dag = normalize_dag


def _normalize_steps(
    dag: list[dict[str, Any]],
    query: str,
    entities: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    query_lower = query.lower()

    for raw_step in dag:
        if not isinstance(raw_step, dict):
            continue

        step = dict(raw_step)
        step_id = str(step.get("step_id") or f"s{len(normalized) + 1}")
        tool_id = step.get("tool_id", "")
        params = dict(step.get("params") or {})
        raw_input_from = dict(step.get("input_from") or {})
        input_from = dict(raw_input_from)
        depends_on = list(step.get("depends_on") or [])

        spec = CAPABILITY_REGISTRY.get(tool_id, {})
        input_schema = spec.get("input_schema", {})
        allowed_params = set(input_schema)
        if allowed_params:
            params = {k: v for k, v in params.items() if k in allowed_params}
            input_from = {k: v for k, v in input_from.items() if k in allowed_params}

        if raw_input_from and not input_from:
            depends_on = []

        previous_lookup = _latest_lookup_step(normalized)
        if previous_lookup:
            source_step, source_tool, source_fields = previous_lookup
            source_step_dict = next(
                (s for s in normalized if str(s.get("step_id")) == source_step),
                {},
            )
            force_from_nl2sql = (
                source_tool == "nl2sql_query"
                and _is_discovery_nl2sql_step(source_step_dict)
            )

            if force_from_nl2sql:
                for param_name in source_fields:
                    if param_name not in input_schema:
                        continue
                    if not _nl2sql_supplies_field(source_step_dict, param_name, query):
                        continue
                    if _entity_supplies_param(entities, param_name, query):
                        continue
                    explicit_value = params.get(param_name)
                    always_wire = param_name in ("product_id", "category")
                    force_date = param_name in ("date", "target_date") and tool_id in (
                        "forecast_explain_drivers",
                        "anomaly_detect",
                        "forecast_predict",
                        "simulate_scenario",
                        "optimize_parameters",
                        "sensitivity_estimate",
                    )
                    needs_wire = (
                        always_wire
                        or force_date
                        or not explicit_value
                        or explicit_value in _PLACEHOLDER_VALUES
                    )
                    if not needs_wire:
                        continue
                    params.pop(param_name, None)
                    input_from[param_name] = {"step": source_step, "field": param_name}
                    if source_step not in depends_on:
                        depends_on.append(source_step)
            else:
                for param_name, schema in input_schema.items():
                    if param_name not in _DISCOVERABLE_FIELDS:
                        continue
                    if param_name not in source_fields:
                        continue
                    if not _lookup_can_supply(source_tool, param_name, step, query):
                        continue

                    explicit_value = params.get(param_name)
                    value_is_user_supplied = (
                        explicit_value and str(explicit_value).lower() in query_lower
                    )
                    value_is_placeholder = (
                        explicit_value in _PLACEHOLDER_VALUES and not value_is_user_supplied
                    )
                    value_is_missing_required = (
                        schema.get("required")
                        and param_name not in params
                        and param_name not in input_from
                    )

                    if value_is_placeholder or value_is_missing_required:
                        params.pop(param_name, None)
                        input_from[param_name] = {"step": source_step, "field": param_name}
                        if source_step not in depends_on:
                            depends_on.append(source_step)

        input_source_steps = _input_source_steps(input_from)
        prior_ids = {str(s.get("step_id")) for s in normalized}
        for src in input_source_steps:
            if src in prior_ids and src not in depends_on:
                depends_on.append(src)
        depends_on = [dep for dep in depends_on if dep in prior_ids]

        normalized.append({
            "step_id": step_id,
            "tool_id": tool_id,
            "params": params,
            "input_from": input_from,
            "depends_on": depends_on,
        })

    return normalized


def _inject_discovery_steps(
    dag: list[dict[str, Any]],
    query: str,
    entities: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Prepend NL2SQL when the first step needs product_id but only has a placeholder."""
    if not dag:
        return dag

    first = dag[0]
    tool_id = first.get("tool_id", "")
    if tool_id == "nl2sql_query":
        return dag

    schema = CAPABILITY_REGISTRY.get(tool_id, {}).get("input_schema", {})
    if not schema.get("product_id", {}).get("required"):
        return dag
    if first.get("input_from", {}).get("product_id"):
        return dag

    product_id = first.get("params", {}).get("product_id")
    if product_id and product_id not in _PLACEHOLDER_VALUES:
        return dag
    if entities and entities.get("product_id") and _PRODUCT_ID_PATTERN.search(query):
        return dag
    if product_id and _PRODUCT_ID_PATTERN.search(query):
        return dag

    discovery_query = (
        f"Find the product_id needed to answer: {query}. Return product_id only."
    )
    discovery_step = {
        "step_id": "s0",
        "tool_id": "nl2sql_query",
        "params": {"query": discovery_query},
        "input_from": {},
        "depends_on": [],
    }

    shifted: list[dict[str, Any]] = [discovery_step]
    for idx, step in enumerate(dag):
        new_id = f"s{idx + 1}"
        old_id = str(step.get("step_id", new_id))
        updated = dict(step)
        updated["step_id"] = new_id

        params = dict(updated.get("params") or {})
        params.pop("product_id", None)
        updated["params"] = params

        input_from = dict(updated.get("input_from") or {})
        if "product_id" not in input_from:
            input_from["product_id"] = {"step": "s0", "field": "product_id"}
        updated["input_from"] = input_from

        depends_on = [
            "s0" if dep == old_id else dep
            for dep in (updated.get("depends_on") or [])
        ]
        if "s0" not in depends_on:
            depends_on.insert(0, "s0")
        updated["depends_on"] = depends_on
        shifted.append(updated)

    return shifted


def _sanitize_input_from(
    dag: list[dict[str, Any]],
    query: str,
) -> list[dict[str, Any]]:
    """Drop input_from mappings whose source step cannot actually supply the field."""
    if not dag:
        return dag

    step_by_id = {str(s.get("step_id")): s for s in dag}
    updated: list[dict[str, Any]] = []

    for step in dag:
        step_copy = dict(step)
        input_from = dict(step_copy.get("input_from") or {})
        depends_on = list(step_copy.get("depends_on") or [])

        for param_name, mapping in list(input_from.items()):
            if isinstance(mapping, dict):
                source_step = str(mapping.get("step", ""))
                source_field = mapping.get("field") or param_name
            else:
                parts = str(mapping).split(".", 1)
                source_step = parts[0]
                source_field = parts[1] if len(parts) == 2 else param_name

            source = step_by_id.get(source_step, {})
            if not source or not _step_can_supply_field(source, source_field, query):
                input_from.pop(param_name, None)
                if source_step in depends_on and not any(
                    (input_from.get(k, {}).get("step") if isinstance(input_from.get(k), dict) else "")
                    == source_step
                    for k in input_from
                ):
                    depends_on = [d for d in depends_on if d != source_step]

        step_copy["input_from"] = input_from
        step_copy["depends_on"] = depends_on
        updated.append(step_copy)

    return updated


def _fill_required_params(
    dag: list[dict[str, Any]],
    query: str,
    entities: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Fill missing required params using entities, prior steps, or safe defaults."""
    if not dag:
        return dag

    from src.core.nl2sql.dates import get_reference_date

    step_by_id = {str(s.get("step_id")): s for s in dag}
    updated: list[dict[str, Any]] = []

    for idx, step in enumerate(dag):
        step_copy = dict(step)
        tool_id = step_copy.get("tool_id", "")
        schema = CAPABILITY_REGISTRY.get(tool_id, {}).get("input_schema", {})
        params = dict(step_copy.get("params") or {})
        input_from = dict(step_copy.get("input_from") or {})
        depends_on = list(step_copy.get("depends_on") or [])

        for param_name, spec in schema.items():
            if not spec.get("required"):
                continue

            if param_name in input_from:
                mapping = input_from[param_name]
                source_step_id = (
                    str(mapping.get("step"))
                    if isinstance(mapping, dict)
                    else str(mapping).split(".", 1)[0]
                )
                source = step_by_id.get(source_step_id, {})
                if not _step_can_supply_field(source, param_name, query):
                    input_from.pop(param_name, None)
                    if source_step_id in depends_on and not any(
                        (input_from.get(k, {}).get("step") if isinstance(input_from.get(k), dict) else "")
                        == source_step_id
                        for k in input_from
                    ):
                        depends_on = [d for d in depends_on if d != source_step_id]

            if param_name in params or param_name in input_from:
                continue

            entity_val = None
            if entities:
                entity_val = entities.get(param_name)
                if entity_val is None and param_name == "target_date":
                    entity_val = entities.get("date")

            if entity_val is not None:
                if param_name in ("date", "target_date"):
                    from src.core.nl2sql.dates import resolve_date
                    parsed = resolve_date(entity_val)
                    if parsed is not None:
                        params[param_name] = parsed.strftime("%Y-%m-%d")
                        continue
                else:
                    params[param_name] = entity_val
                    continue

            if param_name in ("date", "target_date"):
                for prior in reversed(dag[:idx]):
                    prior_id = str(prior.get("step_id"))
                    prior_tool = prior.get("tool_id", "")
                    if prior_tool in ("forecast_predict", "analytics_trend", "anomaly_rank_products"):
                        input_from[param_name] = {"step": prior_id, "field": param_name}
                        if prior_id not in depends_on:
                            depends_on.append(prior_id)
                        break
                else:
                    params[param_name] = get_reference_date().strftime("%Y-%m-%d")

            elif param_name == "product_id" and entities and entities.get("product_id"):
                if _query_explicitly_targets_product(query, str(entities["product_id"])):
                    params["product_id"] = entities["product_id"]

        step_copy["params"] = params
        step_copy["input_from"] = input_from
        step_copy["depends_on"] = depends_on
        updated.append(step_copy)

    return updated


def _step_can_supply_field(
    source_step: dict[str, Any],
    field: str,
    user_query: str,
) -> bool:
    """Whether a planned source step is expected to expose `field` in its output."""
    tool_id = source_step.get("tool_id", "")
    if tool_id == "nl2sql_query":
        return _nl2sql_supplies_field(source_step, field, user_query)
    if tool_id == "forecast_predict":
        return field in ("product_id", "date", "target_date")
    if tool_id == "analytics_trend":
        return field in ("date", "target_date")
    if tool_id == "anomaly_rank_products":
        return field in ("product_id", "date", "target_date")
    if tool_id == "anomaly_detect":
        return field in ("product_id", "date", "target_date")
    return field in ("product_id", "category", "date", "target_date")


def _nl2sql_supplies_field(
    step: dict[str, Any],
    field: str,
    user_query: str = "",
) -> bool:
    """True when an NL2SQL step's query is expected to return this field."""
    query_text = str(step.get("params", {}).get("query", "")).lower()
    combined = f"{query_text} {user_query.lower()}"

    if field == "product_id":
        return (
            "product_id" in combined
            or _PRODUCT_ID_PATTERN.search(combined) is not None
            or _is_discovery_nl2sql_step(step)
        )
    if field == "category":
        return "category" in combined
    if field in ("date", "target_date"):
        if re.search(r"\bselect\b", query_text):
            select_match = re.search(r"\bselect\b(.*?)\bfrom\b", query_text, re.I | re.S)
            if select_match:
                select_cols = select_match.group(1).lower()
                if "date" in select_cols or _DATE_LITERAL.search(select_cols):
                    return True
            return False
        if _DATE_LITERAL.search(combined):
            return True
        if re.search(r"\breturn\b[^.]*\bdate\b", combined):
            return True
        if "date" in combined and _is_discovery_nl2sql_step(step):
            return True
        return False
    return False


def _query_targets_discovery(query: str) -> bool:
    return bool(
        re.search(
            r"\b(worst|best|top|largest|smallest|most|least|biggest|highest|lowest|rank)\b",
            query,
            re.I,
        )
    )


def _query_explicitly_targets_product(query: str, product_id: str) -> bool:
    if _query_targets_discovery(query):
        return False
    return str(product_id).lower() in query.lower()


def _entity_supplies_param(
    entities: dict[str, Any] | None,
    param_name: str,
    query: str,
) -> bool:
    """True when the user query already provides this parameter."""
    if not entities:
        return False
    query_lower = query.lower()
    if param_name == "product_id":
        pid = entities.get("product_id")
        return bool(pid and _query_explicitly_targets_product(query, str(pid)))
    if param_name in ("date", "target_date"):
        date_val = entities.get("date") or entities.get("target_date")
        if not date_val:
            return False
        return str(date_val) in query or _DATE_LITERAL.search(query) is not None
    return False


def _latest_lookup_step(
    steps: list[dict[str, Any]],
) -> tuple[str, str, set[str]] | None:
    """Return the latest previous step that can expose discoverable fields."""
    for step in reversed(steps):
        step_id = str(step.get("step_id"))
        tool_id = step.get("tool_id", "")
        if tool_id == "nl2sql_query":
            return step_id, tool_id, {"product_id", "category", "date", "target_date"}
        if tool_id == "anomaly_rank_products":
            return step_id, tool_id, {"product_id"}
    return None


def _is_discovery_nl2sql_step(step: dict[str, Any]) -> bool:
    query_text = str(step.get("params", {}).get("query", ""))
    return bool(_DISCOVERY_QUERY.search(query_text))


def _lookup_can_supply(
    source_tool: str,
    field: str,
    target_step: dict[str, Any],
    user_query: str,
) -> bool:
    if field in ("product_id", "category"):
        return True
    if field not in ("date", "target_date"):
        return False
    if source_tool == "anomaly_rank_products":
        return field == "target_date" and "target_date" in target_step.get("params", {})
    combined = " ".join([
        user_query,
        str(target_step.get("params", {}).get("query", "")),
    ]).lower()
    return any(term in combined for term in _TEMPORAL_TERMS)


def _input_source_steps(input_from: dict[str, Any]) -> set[str]:
    steps: set[str] = set()
    for mapping in input_from.values():
        if isinstance(mapping, dict) and mapping.get("step"):
            steps.add(str(mapping["step"]))
        elif isinstance(mapping, str) and mapping:
            steps.add(mapping.split(".", 1)[0])
    return steps
