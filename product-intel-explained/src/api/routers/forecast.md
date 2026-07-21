# Forecast Router (`src/api/routers/forecast.py`)

This router provides endpoints to request forecasts and run offline training.

- **What it does**: Exposes GET `/forecast` to predict KPIs over a given horizon, and POST `/forecast/train` to trigger model retraining.
- **Why it exists**: Serves as the primary endpoint for standard forecasting, and enables model updates when new data arrives.
- **Why it was written this way**: Maps endpoints to the `ProductForecaster` engine and calls pipeline training functions.
- **Execution flow**: 
  - GET `/forecast`: fetches data, runs `forecaster.forecast()`, and returns predictions with confidence intervals.
  - POST `/forecast/train`: runs `train_pipeline()` in a background worker or process.
- **Dependencies**: `ProductForecaster`, Pydantic models.
- **Inputs**: HTTP parameters (`product_id`, `horizon_days`), training configurations.
- **Outputs**: Time-series forecast arrays or training success reports.
- **Interview explanation**: "This router handles forecast requests and updates. It exposes endpoints to predict future performance metrics with confidence intervals, and triggers offline model retraining."
- **Concepts used**: Time-series forecasting, async endpoints.
- **Common interview questions**: *"How do you handle long-running operations like model training inside an API router?"* (We execute them as background tasks via FastAPI's `BackgroundTasks` or message queues like Celery, returning a `202 Accepted` status immediately to avoid blocking the client).
