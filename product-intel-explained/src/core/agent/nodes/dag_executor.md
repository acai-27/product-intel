# DAG Executor Node (`src/core/agent/nodes/dag_executor.py`)

This node runs the planned tasks in order.

- **What it does**: Iterates through the steps in the execution plan and invokes the corresponding engine methods (e.g., calling `ProductForecaster` or `ScenarioSimulator`).
- **Why it exists**: Executes the planned calculations to collect the raw analytical data.
- **Interview explanation**: "The executor runs our planned tasks. It loops through each step in the DAG and calls the corresponding Python engine, collecting the raw mathematical outputs."
- **Concepts used**: Dynamic execution, step-by-step iteration.
