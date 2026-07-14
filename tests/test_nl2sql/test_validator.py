"""Tests for NL2SQL SQL validation."""

import pytest

from src.core.nl2sql.validator import SQLValidationError, validate_sql


class TestValidateSQL:
    def test_accepts_simple_select(self) -> None:
        sql = validate_sql(
            "SELECT product_id, SUM(revenue) AS total FROM product_performance "
            "GROUP BY product_id ORDER BY total DESC"
        )
        assert "LIMIT 100" in sql.upper()

    def test_preserves_existing_limit(self) -> None:
        sql = validate_sql(
            "SELECT * FROM product_performance LIMIT 10"
        )
        assert "LIMIT 10" in sql.upper()

    def test_caps_excessive_limit(self) -> None:
        sql = validate_sql(
            "SELECT * FROM product_performance LIMIT 500"
        )
        assert "LIMIT 100" in sql.upper()

    def test_rejects_insert(self) -> None:
        with pytest.raises(SQLValidationError, match="Only SELECT"):
            validate_sql("INSERT INTO product_performance VALUES (1)")

    def test_rejects_delete(self) -> None:
        with pytest.raises(SQLValidationError, match="Only SELECT"):
            validate_sql("DELETE FROM product_performance")

    def test_rejects_unknown_table(self) -> None:
        with pytest.raises(SQLValidationError, match="disallowed"):
            validate_sql("SELECT * FROM users")

    def test_rejects_multiple_statements(self) -> None:
        with pytest.raises(SQLValidationError, match="Multiple"):
            validate_sql("SELECT 1; SELECT 2 FROM product_performance")

    def test_rejects_experiment_report_join(self) -> None:
        with pytest.raises(SQLValidationError, match="disallowed"):
            validate_sql(
                "SELECT e.experiment_id, r.human_readable_text "
                "FROM experiments e JOIN reports r ON r.experiment_id = e.id"
            )

    def test_accepts_events_table(self) -> None:
        sql = validate_sql(
            "SELECT event_type, COUNT(*) AS cnt FROM events GROUP BY event_type"
        )
        assert "events" in sql.lower()
