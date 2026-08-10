"""
SQL validator — enforces read-only, allowlisted queries before execution.

Validation is AST-based: the query is parsed with sqlglot and inspected as a
syntax tree instead of being pattern-matched with regexes. This closes the
bypasses that text matching cannot see — implicit comma joins, data-modifying
CTEs, quoted identifiers, and keywords hidden behind comments — and lets LIMIT
be enforced structurally rather than by string rewriting.

The returned SQL is regenerated from the validated tree, so what executes is
exactly what was inspected.
"""

from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from src.core.nl2sql.schema import ALLOWED_TABLES

_DEFAULT_LIMIT = 100

# Statement roots that may be executed. Everything else (INSERT, DELETE,
# PRAGMA, ...) parses to a different node type and is rejected outright.
_ALLOWED_ROOTS: tuple[type[exp.Expression], ...] = (
    exp.Select,
    exp.SetOperation,  # UNION / EXCEPT / INTERSECT of SELECTs
    exp.Subquery,
)

# Nodes that mutate state or otherwise escape the read-only contract. Checked
# across the whole tree, not just the root, so a data-modifying CTE cannot hide
# under a SELECT root:
#     WITH t AS (DELETE FROM product_performance RETURNING *) SELECT * FROM t
_FORBIDDEN_NODES: tuple[type[exp.Expression], ...] = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.TruncateTable,
    exp.Merge,
    exp.Grant,
    exp.Revoke,
    exp.Command,  # anything sqlglot could not parse into a known statement
    exp.Pragma,
    exp.Set,
    exp.Use,
    exp.Copy,
    exp.Attach,
    exp.Detach,
    exp.Transaction,
    exp.Commit,
    exp.Rollback,
    exp.Cache,
    exp.Uncache,
    exp.Refresh,
    exp.Analyze,
    exp.Describe,
    exp.Export,
    exp.Put,
    exp.Kill,
)

# SQLAlchemy dialect names (engine.dialect.name) → sqlglot dialect names.
_DIALECT_ALIASES = {
    "postgresql": "postgres",
    "postgres": "postgres",
    "psycopg2": "postgres",
    "sqlite": "sqlite",
}


class SQLValidationError(ValueError):
    """Raised when generated SQL fails safety checks."""


def _sqlglot_dialect(dialect: str | None) -> str | None:
    """Map a SQLAlchemy dialect name onto sqlglot's. None means generic SQL."""
    if not dialect:
        return None
    name = dialect.split("+")[0].strip().lower()
    return _DIALECT_ALIASES.get(name, name)


def validate_sql(
    sql: str,
    allowed_tables: frozenset[str] | None = None,
    dialect: str | None = None,
) -> str:
    """
    Validate and normalize a SQL query.

    Returns the SQL regenerated from the validated AST, with LIMIT enforced.
    Raises SQLValidationError on unsafe or unparseable input.
    """
    if not sql or not sql.strip():
        raise SQLValidationError("Empty SQL query.")

    allowed = allowed_tables or ALLOWED_TABLES
    read_dialect = _sqlglot_dialect(dialect)

    try:
        statements = [s for s in sqlglot.parse(sql, dialect=read_dialect) if s is not None]
    except ParseError as e:
        raise SQLValidationError(f"Could not parse SQL: {e}") from e

    if not statements:
        raise SQLValidationError("Empty SQL query.")

    if len(statements) > 1:
        raise SQLValidationError("Multiple statements are not allowed.")

    statement = statements[0]

    if not isinstance(statement, _ALLOWED_ROOTS):
        raise SQLValidationError("Only SELECT queries are allowed.")

    if next(statement.find_all(*_FORBIDDEN_NODES), None) is not None:
        raise SQLValidationError("Query contains forbidden keywords.")

    # SELECT ... INTO creates a table, so it is a write despite the SELECT root.
    if statement.args.get("into"):
        raise SQLValidationError("Only SELECT queries are allowed.")

    referenced = _referenced_tables(statement)

    unknown = referenced - allowed
    if unknown:
        raise SQLValidationError(f"Query references disallowed tables: {sorted(unknown)}")

    if not referenced:
        raise SQLValidationError("Query must reference at least one allowed table.")

    validated = _enforce_limit(statement, _DEFAULT_LIMIT)
    return validated.sql(dialect=read_dialect, comments=False)


def _referenced_tables(statement: exp.Expression) -> set[str]:
    """
    Collect every real table referenced anywhere in the tree.

    CTE names also parse as tables, so they are excluded — they resolve to the
    CTE body, whose own tables are validated separately.
    """
    cte_names = {
        cte.alias_or_name.lower()
        for cte in statement.find_all(exp.CTE)
        if cte.alias_or_name
    }

    tables: set[str] = set()
    for table in statement.find_all(exp.Table):
        name = table.name.lower()
        if name and name not in cte_names:
            tables.add(name)
    return tables


def _enforce_limit(statement: Any, max_limit: int) -> Any:
    """Add LIMIT when absent, and cap it when it exceeds max_limit."""
    limit = statement.args.get("limit")
    if limit is None:
        return statement.limit(max_limit)

    try:
        current = int(limit.expression.name)
    except (AttributeError, TypeError, ValueError):
        # Non-literal limit (parameter, expression) — replace with a known bound.
        return statement.limit(max_limit)

    if current > max_limit:
        return statement.limit(max_limit)
    return statement
