# DAG Planner Node (`src/core/agent/nodes/dag_planner.py`)

This node translates user queries into execution plans.

- **What it does**: Creates a Directed Acyclic Graph (DAG) plan detailing which engines to run and in what order (e.g., forecasting first, then running the explainer).
- **Why it exists**: Formulates structured, step-by-step plans for complex questions, allowing the system to run multiple engines in sequence.
- **Interview explanation**: "This node acts as our planner. It translates the user's question into a structured execution plan (a DAG) of tools, ensuring we run tasks in the correct logical order."
- **Concepts used**: Automated planning, sequence generation.
