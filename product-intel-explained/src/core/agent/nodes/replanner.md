# Replanning Node (`src/core/agent/nodes/replanner.py`)

This node adjusts execution plans when validation checks fail.

- **What it does**: Inspects validation errors and generates a corrected execution plan with adjusted settings.
- **Why it exists**: Enables self-correction, letting the agent automatically repair issues without needing user intervention.
- **Interview explanation**: "If validation checks fail, this node inspects the errors and updates the execution plan, letting the agent self-repair and recalculate."
- **Concepts used**: Self-correction loops, error mitigation.
