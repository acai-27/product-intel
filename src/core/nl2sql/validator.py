"""
SQL validator — enforces read-only, allowlisted queries before execution.

Note: This validator uses regex and keyword-based validation rather than AST parsing
or libraries like sqlglot/sqlparse. It sanitizes input by removing comments, checking for
forbidden keywords (e.g. INSERT, DELETE, DROP), verifying table allowlists via simple regexes,
and enforcing SELECT-only statements with LIMIT clauses.
"""

import re
from typing import Optional

from src.core.nl2sql.schema import ALLOWED_TABLES

_FORBIDDEN_KEYWORDS = re.compile(
    r"\b("
    r"INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|REPLACE|MERGE|"
    r"GRANT|REVOKE|EXEC|EXECUTE|CALL|COPY|INTO|ATTACH|DETACH|PRAGMA"
    r")\b",
    re.IGNORECASE,
)

_DEFAULT_LIMIT = 100


class SQLValidationError(ValueError):
    """Raised when generated SQL fails safety checks."""


def validate_sql(sql: str, allowed_tables: frozenset[str] | None = None) -> str:
    """
    Validate and normalize a SQL query.

    Returns the sanitized SQL (with LIMIT enforced if missing).
    Raises SQLValidationError on unsafe input.
    """
    if not sql or not sql.strip():
        raise SQLValidationError("Empty SQL query.")

    allowed = allowed_tables or ALLOWED_TABLES
    normalized = _strip_comments(sql.strip()).rstrip(";").strip()

    if ";" in normalized:
        raise SQLValidationError("Multiple statements are not allowed.")

    if not re.match(r"^SELECT\b", normalized, re.IGNORECASE):
        raise SQLValidationError("Only SELECT queries are allowed.")

    if _FORBIDDEN_KEYWORDS.search(normalized):
        raise SQLValidationError("Query contains forbidden keywords.")

    referenced = _extract_table_names(normalized)
    unknown = referenced - allowed
    if unknown:
        raise SQLValidationError(f"Query references disallowed tables: {sorted(unknown)}")

    if not referenced:
        raise SQLValidationError("Query must reference at least one allowed table.")

    return _ensure_limit(normalized, _DEFAULT_LIMIT)


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"--[^\n]*", " ", sql)
    return sql


_TABLE_REF = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
_FROM_JOIN_INTRO = re.compile(r"\b(?:FROM|JOIN)\s+", re.IGNORECASE)
_CLAUSE_BOUNDARY = re.compile(
    r"\b(?:WHERE|GROUP|ORDER|HAVING|LIMIT|UNION|JOIN|ON|USING)\b|\)",
    re.IGNORECASE,
)


def _extract_table_names(sql: str) -> set[str]:
    """
    Extract table names from FROM and JOIN clauses.

    Handles comma-separated FROM lists (implicit joins) so that a disallowed
    table cannot slip past the allowlist via `FROM allowed_table, secret_table`.
    """
    tables: set[str] = set()
    for intro in _FROM_JOIN_INTRO.finditer(sql):
        segment = sql[intro.end():]
        boundary = _CLAUSE_BOUNDARY.search(segment)
        if boundary:
            segment = segment[: boundary.start()]
        for part in segment.split(","):
            part = part.strip()
            if not part or part.startswith("("):
                continue
            token = _TABLE_REF.match(part)
            if token:
                tables.add(token.group(0).lower())
    return tables


def _ensure_limit(sql: str, max_limit: int) -> str:
    if re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        limit_match = re.search(r"\bLIMIT\s+(\d+)", sql, re.IGNORECASE)
        if limit_match and int(limit_match.group(1)) > max_limit:
            return re.sub(
                r"\bLIMIT\s+\d+",
                f"LIMIT {max_limit}",
                sql,
                count=1,
                flags=re.IGNORECASE,
            )
        return sql
    return f"{sql} LIMIT {max_limit}"
