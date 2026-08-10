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


class TestAllowlistBypasses:
    """Bypasses that only AST-level inspection can catch."""

    def test_rejects_implicit_comma_join(self) -> None:
        with pytest.raises(SQLValidationError, match="disallowed"):
            validate_sql("SELECT * FROM product_performance, users")

    def test_rejects_aliased_implicit_comma_join(self) -> None:
        with pytest.raises(SQLValidationError, match="disallowed"):
            validate_sql(
                "SELECT pp.revenue FROM product_performance pp, secret_users s "
                "WHERE pp.product_id = s.pid"
            )

    def test_rejects_quoted_disallowed_table(self) -> None:
        with pytest.raises(SQLValidationError, match="disallowed"):
            validate_sql('SELECT * FROM product_performance, "users"')

    def test_rejects_disallowed_table_in_subquery(self) -> None:
        with pytest.raises(SQLValidationError, match="disallowed"):
            validate_sql(
                "SELECT product_id FROM product_performance "
                "WHERE product_id IN (SELECT pid FROM users)"
            )

    def test_rejects_disallowed_table_in_union(self) -> None:
        with pytest.raises(SQLValidationError, match="disallowed"):
            validate_sql(
                "SELECT product_id FROM product_performance "
                "UNION SELECT pid FROM users"
            )

    def test_rejects_data_modifying_cte(self) -> None:
        with pytest.raises(SQLValidationError, match="forbidden"):
            validate_sql(
                "WITH t AS (DELETE FROM product_performance RETURNING *) "
                "SELECT * FROM t"
            )

    def test_rejects_select_into(self) -> None:
        with pytest.raises(SQLValidationError, match="Only SELECT"):
            validate_sql("SELECT * INTO copy_tbl FROM product_performance")

    def test_rejects_unparseable_sql(self) -> None:
        with pytest.raises(SQLValidationError):
            validate_sql("SELECT FROM WHERE ((((")


class TestValidSqlIsPreserved:
    def test_allows_cte_referencing_allowed_table(self) -> None:
        sql = validate_sql(
            "WITH top AS (SELECT product_id, SUM(revenue) AS r "
            "FROM product_performance GROUP BY product_id) "
            "SELECT * FROM top ORDER BY r DESC"
        )
        assert "product_performance" in sql.lower()
        assert "LIMIT 100" in sql.upper()

    def test_allows_join_between_allowed_tables(self) -> None:
        sql = validate_sql(
            "SELECT p.product_id, e.event_type FROM product_performance p "
            "JOIN events e ON e.product_id = p.product_id"
        )
        assert "LIMIT 100" in sql.upper()

    def test_strips_comments_from_output(self) -> None:
        sql = validate_sql(
            "SELECT revenue FROM product_performance -- trailing note"
        )
        assert "--" not in sql
        assert "trailing note" not in sql

    def test_preserves_where_and_offset(self) -> None:
        sql = validate_sql(
            "SELECT date, revenue FROM product_performance "
            "WHERE product_id = 'P001' ORDER BY date DESC LIMIT 500 OFFSET 5"
        )
        assert "'P001'" in sql
        assert "OFFSET 5" in sql.upper()
        assert "LIMIT 100" in sql.upper()

    def test_dialect_is_accepted(self) -> None:
        sql = validate_sql(
            "SELECT SUM(revenue) AS total FROM product_performance",
            dialect="postgresql",
        )
        assert "LIMIT 100" in sql.upper()
