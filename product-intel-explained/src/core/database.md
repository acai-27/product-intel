# Database Connection Manager (`src/core/database.py`)

This file manages connection pools and database sessions.

- **What it does**: Establishes connection sessions to Neon database layers.
- **Why it exists**: Manages database connections efficiently, reusing them to prevent resource leaks.
- **Why it was written this way**: Sets connection pool tuning properties (`pool_pre_ping=True`, `pool_recycle=300`) to handle cold-starts and connection drops.
- **Execution flow**: 
  - Standard route: calls `get_db()`, yields session, and closes it upon route termination.
  - direct psycopg2 logic runs via `get_neon_connection()`.
- **Dependencies**: `SQLAlchemy`, `psycopg2`, `.env` profiles.
- **Inputs**: Environment variable configurations.
- **Outputs**: Active database sessions.
- **Interview explanation**: "This file manages connections to our serverless database. I configured SQLAlchemy with connection pre-pings and connection recycling to handle serverless cold starts gracefully."
- **Concepts used**: Connection pooling, session cleanup, database transactions.
- **Common interview questions**: *"What is connection pre-pinging?"* (It sends a lightweight check query (like `SELECT 1`) to verify a connection is alive before using it, preventing broken connection errors).
