# NL2SQL Engine Modules (`src/core/nl2sql/`)

This directory translates natural language queries to SQL.

- **What it does**: Generates, validates, and executes database queries from natural language text.
- **Why it exists**: Allows users to request raw facts directly from our database without needing to write SQL.
- **Important files**:
  - `engine.py`: Coordinates generation and execution.
  - `generator.py`: Generates SQL commands using LLMs (Gemma via NIM).
  - `validator.py`: Enforces security policies using keyword and regex checks.
  - `executor.py`: Executes queries safely using read-only connections.
  - `dates.py`: Parses relative date terms (like 'last week') into calendar ranges.
- **Interview explanation**: "This engine translates natural language to SQL queries. It uses a regex validator to block destructive SQL commands, parses relative date terms, and runs queries on a read-only database connection."
- **Concepts used**: Prompt-driven SQL generation, query sanitization, relative date resolution.
- **Common interview questions**: *"How do you prevent SQL injection in an automated NL2SQL engine?"* (We enforce strict parameter validation, run queries on a read-only database user, block write keywords with regex, and limit returned rows).
