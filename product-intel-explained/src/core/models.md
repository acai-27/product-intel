# SQL Alchemy Model Schema Definitions (`src/core/models.py`)

This file contains ORM mappings matching PostgreSQL performance metrics table.

- **What it does**: Declares SQLAlchemy models representing our database tables, defining column types, keys, and indexes.
- **Why it exists**: Maps database table records directly to Python objects.
- **Why it was written this way**: Inherits from a declarative base (`Base`) and defines indexes on frequently queried columns (like `product_id` and `date`) to speed up database reads.
- **Dependencies**: `SQLAlchemy`, `database.py` Base.
- **Inputs**: Database records.
- **Outputs**: Instantiated Python ORM model objects.
- **Interview explanation**: "This file defines our database models using SQLAlchemy. I added composite database indexes on columns like `product_id` and `date` to ensure that our historical data queries remain fast even as our tables grow."
- **Concepts used**: ORM mapping, index optimization, database constraints.
- **Common interview questions**: *"How do indexes improve query speed, and what is the trade-off?"* (Indexes speed up search/read performance by creating structured lookup trees, but they slow down write/insert performance and consume additional disk space).
