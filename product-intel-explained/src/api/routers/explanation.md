# Explainer Router (`src/api/routers/explanation.py`)

This router exposes endpoints to fetch feature importance and prediction drivers.

- **What it does**: Exposes GET `/explanation` to request SHAP-based feature importance for a specific date and target metric.
- **Why it exists**: Feeds the "Why" analysis UI elements, helping users understand what factors (e.g. price change, ad spend) drove a given forecast.
- **Why it was written this way**: Maps incoming queries directly to the `PredictionExplainer` engine using Pydantic schemas.
- **Execution flow**: 
  1. GET `/explanation` is invoked.
  2. Router fetches `PredictionExplainer` and retrieves historical data.
  3. Explainer runs SHAP and returns driver lists and summaries.
- **Dependencies**: `PredictionExplainer`, historical data loaders, Pydantic schemas.
- **Inputs**: HTTP parameters: `product_id`, `target_metric`, `date`.
- **Outputs**: Driver lists grouped into positive and negative impacts, along with a natural language summary.
- **Interview explanation**: "The explanation router handles explainability queries, routing them to the `PredictionExplainer` engine to return SHAP drivers for a specific forecast."
- **Concepts used**: Model explainability, RESTful routing.
