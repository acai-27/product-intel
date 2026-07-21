# Scenario Schemas (`src/api/schemas/scenario.py`)

This file defines data contracts for counterfactual simulations.

- **What it does**: Validates and structures request parameters and output metrics for the What-If simulation engine.
- **Why it exists**: Ensures that modification parameters (such as variable overrides and targets) conform to standard structures.
- **Why it was written this way**: Uses nested models to represent baseline and simulated KPI metrics cleanly.
- **Interview explanation**: "This file defines validation schemas for counterfactual simulations, structuring baseline-to-scenario comparisons and delta percentages across all target KPIs."
- **Concepts used**: Nesting models, contract verification.
