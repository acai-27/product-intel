# Explainability Engine (`src/core/explainer.py`)

This file uses SHAP to calculate feature contributions for forecasts.

- **What it does**: Explains the "why" behind predictions by calculating the marginal contribution of each feature.
- **Why it exists**: Builds trust. Business users need to understand the primary drivers behind a forecast to act on it.
- **Why it was written this way**: Implemented using `TreeExplainer` for high performance with our gradient-boosting models, using a pre-calculated background dataset to anchor calculations.
- **Execution flow**: 
  1. Pulls historical feature values.
  2. Invokes `TreeExplainer` on the prediction row.
  3. Maps raw feature names to business terms (e.g. converting `marketing_spend_lag_7` to 'Ad spend from 7 days ago').
  4. Groups results into positive and negative drivers and generates a summary.
- **Dependencies**: `SHAP`, `ProductForecaster`, Pandas.
- **Inputs**: Historical data, product ID, target metric, date.
- **Outputs**: Positive and negative driver lists, baseline expectations, and a natural language explanation.
- **Interview explanation:** "We use SHAP TreeExplainers to calculate the marginal contribution of each feature. It translates complex lag and rolling features into plain English and highlights the primary positive and negative factors driving the forecast."
- **Concepts used**: SHAP value interpretation, translation mapping.
- **Common interview questions**: *"Why use TreeExplainer instead of KernelExplainer?"* (KernelExplainer is model-agnostic but slow because it relies on sampling. TreeExplainer takes advantage of the tree structure, running in polynomial time for tree models).
