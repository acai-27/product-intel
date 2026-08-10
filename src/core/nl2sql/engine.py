"""
NL2SQL Engine — ask-style natural language to SQL pipeline.

Flow: question → generate SQL → validate → execute → (optional repair retry)

Note: This engine uses the Gemma model (via NVIDIA NIM primary or Ollama fallback)
for SQL generation, rather than Llama 3.1.
"""

from typing import Any

from src.core.llm import LLMClient
from src.core.nl2sql.executor import execute_sql
from src.core.nl2sql.generator import generate_sql
from src.core.nl2sql.validator import SQLValidationError, validate_sql
from src.utils.logger import setup_logger

logger = setup_logger("nl2sql_engine")

_MAX_RETRIES = 1


class NL2SQLEngine:
    """Converts natural language questions into validated SQL and returns results."""

    def __init__(self, llm_client: LLMClient, db_engine: Any) -> None:
        self._llm = llm_client
        self._db_engine = db_engine
        self._dialect = db_engine.dialect.name

    def ask(self, question: str) -> dict[str, Any]:
        """
        Answer a factual data question via NL2SQL.

        Returns structured results suitable for the LangGraph synthesizer.
        """
        question = question.strip()
        if not question:
            return self._error_response(question, "Empty question.")

        last_error: str | None = None
        sql: str | None = None

        for attempt in range(_MAX_RETRIES + 1):
            try:
                sql = generate_sql(
                    self._llm,
                    question,
                    dialect=self._dialect,
                    error_context=last_error if attempt > 0 else None,
                )
                validated_sql = validate_sql(sql, dialect=self._dialect)
                result = execute_sql(self._db_engine, validated_sql)
                return {
                    "query": question,
                    "sql": validated_sql,
                    "columns": result["columns"],
                    "rows": result["rows"],
                    "row_count": result["row_count"],
                    "truncated": result["truncated"],
                }
            except SQLValidationError as e:
                last_error = f"Validation error: {e}"
                logger.warning(last_error)
            except (ValueError, RuntimeError) as e:
                last_error = str(e)
                logger.warning(f"NL2SQL attempt {attempt + 1} failed: {last_error}")

        return self._error_response(question, last_error or "Unknown error.", sql)

    @staticmethod
    def _error_response(
        question: str,
        error: str,
        sql: str | None = None,
    ) -> dict[str, Any]:
        return {
            "query": question,
            "sql": sql,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "truncated": False,
            "error": error,
        }
