# Scenario Simulation Router (`src/api/routers/scenario.py`)

This router exposes endpoints to run What-If scenario simulations.

- **What it does**: Exposes GET `/scenario/simulate` to simulate changes (e.g. pricing, marketing) and measure their impact on KPIs.
- **Why it exists**: Serves the interactive scenario planning tools on the React dashboard.
- **Why it was written this way**: Intercepts modifications and directs them to the `ScenarioSimulator` engine.
- **Execution flow**: 
  1. GET `/scenario/simulate` is called with a list of changes.
  2. Router fetches the simulator instance.
  3. Simulator calculates baseline vs. simulated forecasts.
  4. Returns comparison metrics and absolute/percentage deltas.
- **Dependencies**: `ScenarioSimulator`, historical data loaders.
- **Inputs**: HTTP parameters: `product_id`, `horizon_days`, `changes` (list of strings).
- **Outputs**: Detailed baseline vs. simulated comparison metrics across all target KPIs.
- **Interview explanation**: "This router exposes our What-If simulator. It takes a list of hypothetical change strings, runs them through the simulation engine, and returns comparison metrics showing the ROI of proposed changes."
- **Concepts used**: Counterfactual simulation, array comparison.
