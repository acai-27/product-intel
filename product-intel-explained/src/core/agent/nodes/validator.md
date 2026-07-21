# Results Validator Node (`src/core/agent/nodes/validator.py`)

This node validates prediction outputs against business rules.

- **What it does**: Checks calculation results against logical boundaries (e.g. ensuring predicted profit does not exceed revenue).
- **Why it exists**: Acts as a quality check, catching unrealistic predictions before they reach the user.
- **Interview explanation**: "The validator checks all output values against business logic. If it catches illogical outputs, it flags them so the planner can adjust parameters and try again."
- **Concepts used**: Business logic validation, rule checking.
