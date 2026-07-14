"""
Deterministic Chart.js config builders from tool result payloads.
"""

from __future__ import annotations

import re
from typing import Any, Callable

_PALETTE = [
    "rgba(165, 90, 50, 0.82)",
    "rgba(11, 36, 32, 0.72)",
    "rgba(205, 176, 141, 0.88)",
    "rgba(107, 158, 120, 0.78)",
    "rgba(139, 115, 85, 0.75)",
]
_BORDERS = ["#A55A32", "#0B2420", "#CDB08D", "#6B9E78", "#8B7355"]

_NUMERIC = re.compile(r"^-?\d+(\.\d+)?$")


def _chart(
    *,
    viz_id: str,
    title: str,
    chart_type: str,
    labels: list[str],
    datasets: list[dict[str, Any]],
    subtitle: str = "",
    index_axis: str | None = None,
    source_step: str = "",
    source_tool: str = "",
) -> dict[str, Any]:
    return {
        "id": viz_id,
        "title": title,
        "subtitle": subtitle,
        "chart_type": chart_type,
        "index_axis": index_axis,
        "source_step": source_step,
        "source_tool": source_tool,
        "data": {"labels": labels, "datasets": datasets},
    }


def _dataset(label: str, data: list[float | int], idx: int = 0, fill: bool = False) -> dict[str, Any]:
    color = _PALETTE[idx % len(_PALETTE)]
    border = _BORDERS[idx % len(_BORDERS)]
    return {
        "label": label,
        "data": data,
        "backgroundColor": color if fill else color.replace("0.82", "0.15").replace("0.88", "0.15").replace("0.78", "0.15").replace("0.72", "0.12").replace("0.75", "0.12"),
        "borderColor": border,
        "borderWidth": 2,
        "fill": fill,
        "tension": 0.35,
        "pointRadius": 3,
        "pointHoverRadius": 5,
    }


def build_from_step(step_id: str, tool_id: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(data, dict) or data.get("error"):
        return []
    builders: dict[str, list[Callable[..., list[dict[str, Any]]]]] = {
        "forecast_predict": [_build_forecast],
        "forecast_explain_drivers": [_build_shap],
        "nl2sql_query": [_build_nl2sql],
        "simulate_scenario": [_build_simulation],
        "anomaly_rank_products": [_build_anomaly_rank],
    }
    charts: list[dict[str, Any]] = []
    for fn in builders.get(tool_id, []):
        charts.extend(fn(step_id, tool_id, data))
    return charts


def _build_forecast(step_id: str, tool_id: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = data.get("daily_details") or []
    if not rows:
        return []
    labels = [str(r.get("date", ""))[:10] for r in rows]
    metrics = [k for k in ("revenue", "profit", "orders") if k in rows[0]]
    if not metrics:
        return []
    datasets = [
        _dataset(m.replace("_", " ").title(), [float(r.get(m, 0) or 0) for r in rows], i, fill=(i == 0))
        for i, m in enumerate(metrics)
    ]
    pid = data.get("product_id", "")
    return [_chart(
        viz_id=f"{step_id}_forecast",
        title="Forecast Trajectory",
        subtitle=f"Product {pid} Â· {data.get('horizon_days', 30)}-day horizon" if pid else "",
        chart_type="line",
        labels=labels,
        datasets=datasets,
        source_step=step_id,
        source_tool=tool_id,
    )]


def _build_shap(step_id: str, tool_id: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    drivers: list[dict[str, Any]] = []
    for key in ("positive_drivers", "negative_drivers"):
        for d in data.get(key) or []:
            drivers.append({
                "name": d.get("clean_name") or d.get("feature", "Driver"),
                "value": float(d.get("shap_value", 0) or 0),
            })
    if not drivers:
        return []
    drivers = sorted(drivers, key=lambda x: abs(x["value"]), reverse=True)[:12]
    labels = [d["name"] for d in drivers]
    values = [d["value"] for d in drivers]
    colors = ["rgba(107, 158, 120, 0.75)" if v >= 0 else "rgba(180, 90, 80, 0.75)" for v in values]
    return [_chart(
        viz_id=f"{step_id}_shap",
        title="Driver Impact (SHAP)",
        subtitle=f"{data.get('target_metric', 'revenue').title()} Â· {data.get('date', '')}",
        chart_type="bar",
        index_axis="y",
        labels=labels,
        datasets=[{
            "label": "SHAP contribution",
            "data": values,
            "backgroundColor": colors,
            "borderColor": colors,
            "borderWidth": 0,
        }],
        source_step=step_id,
        source_tool=tool_id,
    )]


def _build_nl2sql(step_id: str, tool_id: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = data.get("rows") or []
    if not rows:
        return []
    columns = data.get("columns") or list(rows[0].keys())
    if len(columns) < 2:
        return []

    label_col = columns[0]
    numeric_cols = [
        c for c in columns[1:]
        if all(_is_numeric(r.get(c)) for r in rows[: min(20, len(rows))])
    ]
    if not numeric_cols:
        return []

    labels = [str(r.get(label_col, ""))[:24] for r in rows[:20]]
    chart_type = "line" if _looks_temporal(label_col, labels) else "bar"
    datasets = [
        _dataset(c.replace("_", " ").title(), [float(r.get(c, 0) or 0) for r in rows[:20]], i)
        for i, c in enumerate(numeric_cols[:3])
    ]
    return [_chart(
        viz_id=f"{step_id}_nl2sql",
        title="Query Results",
        subtitle=f"{data.get('row_count', len(rows))} rows",
        chart_type=chart_type,
        labels=labels,
        datasets=datasets,
        source_step=step_id,
        source_tool=tool_id,
    )]


def _build_simulation(step_id: str, tool_id: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    charts: list[dict[str, Any]] = []
    kpis = data.get("kpis") or {}
    if kpis:
        labels, baseline, simulated = [], [], []
        for name, vals in kpis.items():
            if not isinstance(vals, dict):
                continue
            labels.append(name.replace("_", " ").title())
            baseline.append(float(vals.get("baseline", vals.get("baseline_sum", 0)) or 0))
            simulated.append(float(vals.get("simulated", vals.get("simulated_sum", 0)) or 0))
        if labels:
            charts.append(_chart(
                viz_id=f"{step_id}_sim_kpi",
                title="Scenario Impact by KPI",
                subtitle="Baseline vs simulated",
                chart_type="bar",
                labels=labels,
                datasets=[
                    _dataset("Baseline", baseline, 0),
                    _dataset("Simulated", simulated, 1),
                ],
                source_step=step_id,
                source_tool=tool_id,
            ))

    daily = data.get("daily_comparison") or {}
    if isinstance(daily, dict) and daily:
        first_kpi = next(iter(daily), None)
        if first_kpi and isinstance(daily[first_kpi], list):
            rows = daily[first_kpi][:20]
            labels = [str(r.get("date", i))[:10] for i, r in enumerate(rows)]
            charts.append(_chart(
                viz_id=f"{step_id}_sim_daily",
                title=f"Daily {first_kpi.replace('_', ' ').title()} Comparison",
                chart_type="line",
                labels=labels,
                datasets=[
                    _dataset("Baseline", [float(r.get("baseline", 0) or 0) for r in rows], 0, fill=True),
                    _dataset("Simulated", [float(r.get("simulated", 0) or 0) for r in rows], 1, fill=True),
                ],
                source_step=step_id,
                source_tool=tool_id,
            ))
    return charts


def _build_anomaly_rank(step_id: str, tool_id: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    items = (
        data.get("top_10_critical_products")
        or data.get("most_unusual_products")
        or data.get("top_revenue_risk")
        or []
    )
    if not items:
        return []
    top = items[:10]
    labels = [str(i.get("product_id", "")) for i in top]
    scores = [float(i.get("severity_score", 0) or 0) for i in top]
    return [_chart(
        viz_id=f"{step_id}_anomaly_rank",
        title="Anomaly Severity Ranking",
        chart_type="bar",
        labels=labels,
        datasets=[_dataset("Severity score", scores, 0)],
        source_step=step_id,
        source_tool=tool_id,
    )]


def _is_numeric(val: Any) -> bool:
    if val is None:
        return False
    if isinstance(val, (int, float)):
        return True
    return bool(_NUMERIC.match(str(val).strip()))


def _looks_temporal(col: str, labels: list[str]) -> bool:
    if "date" in col.lower():
        return True
    return bool(labels and re.match(r"\d{4}-\d{2}", str(labels[0])))

