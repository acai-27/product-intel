# Autoregressive Forecasting Engine (`src/core/forecaster.py`)

This file performs recursive forecasting across target KPIs using LightGBM.

- **What it does**: Generates multi-step predictions for KPIs, dynamically recalculating time-series features (like rolling averages) at each step.
- **Why it exists**: Enables long-horizon forecasting by chain-linking daily predictions sequentially.
- **Why it was written this way**: Implemented as an autoregressive loop. It bounds target values (like clipping negative revenue) to ensure outputs conform to business logic.
- **Execution flow**: 
  1. Filters historical data for the requested product.
  2. Applies future parameter overrides (e.g. ad spend adjustments).
  3. Runs an autoregressive loop: transforms data, runs LightGBM, clips negative predictions, and appends the result to history.
  4. Calculates empirical confidence intervals using validation residuals.
- **Dependencies**: `LightGBM`, `TimeSeriesPreprocessor`, Pandas, NumPy.
- **Inputs**: Historical data, product ID, forecast horizon, and future overrides.
- **Outputs**: Forecast dataframe containing predicted targets and confidence bounds.
- **Interview explanation**: "The forecaster uses an autoregressive loop with LightGBM. It predicts one day at a time, appends that prediction to the history, and recalculates features to predict the next day. This ensures rolling averages and lag variables remain accurate across the horizon."
- **Concepts used**: Autoregressive modeling, empirical error calculation, feature transformation pipeline.
- **Common interview questions**: *"What are the risks of autoregressive predictions?"* (Errors compound at each step. A bad prediction on Day 1 will skew rolling features, leading to progressively less accurate forecasts further down the horizon).
