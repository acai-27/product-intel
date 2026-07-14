"""
Integration tests for the full LangGraph pipeline.

Tests the complete flow from query → intent classification → DAG planning
→ execution → synthesis, using mocked LLM and engines.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.core.agent.graph import init_graph, run_agent_graph, _compiled_graph
import src.core.agent.graph as graph_module


@pytest.fixture(autouse=True)
def reset_graph():
    """Reset graph state before each test."""
    graph_module._compiled_graph = None
    graph_module._llm_client = None
    graph_module._engines = {}
    yield
    graph_module._compiled_graph = None
    graph_module._llm_client = None
    graph_module._engines = {}


def _mock_engines() -> dict:
    """Create minimal mock engines for testing."""
    return {
        "forecaster": MagicMock(),
        "explainer": MagicMock(),
        "simulator": MagicMock(),
        "anomaly_engine": MagicMock(),
        "nl2sql_engine": MagicMock(),
    }


class TestGreetingFlow:
    """Test that greetings bypass all engines and return a fast response."""

    def test_greeting_returns_fast(self) -> None:
        mock_llm = MagicMock()
        init_graph(mock_llm, _mock_engines())

        result = run_agent_graph("hello")

        assert result["intent"] == "greeting"
        assert result["route_called"] == "greeting"
        assert result["final_response"] == ""
        # LLM should NOT be called for greetings
        mock_llm.generate_json.assert_not_called()
        mock_llm.generate.assert_not_called()


class TestGuardrailBlock:
    """Test that out-of-scope queries are blocked."""

    def test_out_of_scope_blocked(self) -> None:
        mock_llm = MagicMock()
        mock_llm.generate_json.return_value = {
            "intent": "out_of_scope",
            "confidence": 0.9,
            "extracted_params": {},
        }
        init_graph(mock_llm, _mock_engines())

        result = run_agent_graph("Write me a Python game")

        assert result["intent"] == "out_of_scope"
        assert result["is_blocked"] is True
        assert result["route_called"] == "guardrail_block"


class TestAnalyticalFlow:
    """Test that analytical queries go through the full DAG pipeline."""

    def test_forecast_uses_llm_planner(self) -> None:
        mock_llm = MagicMock()
        mock_llm.generate_json.side_effect = [
            {
                "intent": "analytical",
                "confidence": 0.95,
                "extracted_params": {
                    "product_id": "P001",
                    "target_metric": "revenue",
                    "query": "Forecast revenue for P001",
                },
            },
            {
                "reasoning": "Single-step forecast for P001.",
                "dag": [{
                    "step_id": "s1",
                    "tool_id": "forecast_predict",
                    "params": {"product_id": "P001", "horizon_days": 30},
                    "depends_on": [],
                }],
            },
        ]
        engines = _mock_engines()
        import pandas as pd
        engines["forecaster"].forecast.return_value = pd.DataFrame({
            "date": pd.date_range("2025-02-01", periods=3),
            "revenue": [100.0, 110.0, 120.0],
            "profit": [40.0, 44.0, 48.0],
            "orders": [10, 11, 12],
        })

        init_graph(mock_llm, engines)

        with patch("src.core.agent.nodes.tool_nodes._get_data") as mock_data:
            mock_data.return_value = pd.DataFrame({
                "date": pd.date_range("2025-01-01", periods=30),
                "product_id": ["P001"] * 30,
                "revenue": [100.0] * 30,
            })
            result = run_agent_graph("Forecast revenue for P001")

        assert result["dag_source"] == "dynamic"
        assert result["route_called"] == "forecast_predict"
        assert "forecast_total_revenue" in result["raw_data"]["s1"]
        mock_llm.generate_json.assert_called()


class TestDataLookupFlow:
    """Test NL2SQL data_lookup intent through the LangGraph pipeline."""

    def test_data_lookup_uses_fast_path_dag(self) -> None:
        mock_llm = MagicMock()

        engines = _mock_engines()
        engines["nl2sql_engine"].ask.return_value = {
            "query": "Total revenue for P001",
            "sql": "SELECT SUM(revenue) AS total FROM product_performance WHERE product_id = 'P001' LIMIT 1",
            "columns": ["total"],
            "rows": [{"total": 220.0}],
            "row_count": 1,
            "truncated": False,
        }

        init_graph(mock_llm, engines)
        result = run_agent_graph("What is the total revenue for P001?")

        assert result["dag_source"] == "regex_fast_path"
        assert result["route_called"] == "nl2sql_query"
        assert result["raw_data"]["s1"]["row_count"] == 1
        engines["nl2sql_engine"].ask.assert_called_once()


class TestGraphInitialization:
    """Test graph lifecycle."""

    def test_run_without_init_raises(self) -> None:
        with pytest.raises(RuntimeError, match="not initialized"):
            run_agent_graph("hello")

    def test_double_init_is_safe(self) -> None:
        mock_llm = MagicMock()
        engines = _mock_engines()
        init_graph(mock_llm, engines)
        init_graph(mock_llm, engines)  # Should not raise
