# Scenario Simulation Engine (`src/core/simulator.py`)

This file runs What-If counterfactual scenario simulations.

- **What it does**: Compares baseline predictions against a simulated forecast where specific variables (like marketing spend) have been modified.
- **Why it exists**: Allows users to test the impact of pricing or marketing changes before committing budget.
- **Why it was written this way**: Parses natural language strings into mathematical modifications, runs control and treatment forecasts, and returns the deltas.
- **Execution flow**: 
  1. Parses modification strings (e.g. 'discount +5%') using regular expressions.
  2. Runs a baseline forecast.
  3. Applies modifications to create a `future_overrides` dictionary.
  4. Runs a simulated forecast with overrides.
  5. Computes absolute and percentage differences between the baseline and simulation.
- **Dependencies**: `ProductForecaster`, Pandas, NumPy.
- **Inputs**: Historical data, product ID, horizon, change strings.
- **Outputs**: KPI summaries and daily comparison records.
- **Interview explanation**: "The simulator acts as a wrapper around our forecasting engine. It runs a baseline forecast, then parses a string like 'discount +5%', overrides that variable in a secondary forecast, and returns the absolute and percentage differences across all KPIs."
- **Concepts used**: Counterfactual comparison, regex pattern matching, variance analysis.
- **Common interview questions**: *"How do you test scenario changes without corrupting your database?"* (We apply overrides in memory at the model input layer rather than writing changes to the underlying database tables).
