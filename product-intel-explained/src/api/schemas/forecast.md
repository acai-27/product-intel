# Forecast Schemas (`src/api/schemas/forecast.py`)

This file defines validation contracts for forecasting requests and responses.

- **What it does**: Enforces input bounds (e.g. validating that `horizon_days` is a positive integer) and structures prediction payloads.
- **Why it exists**: Protects the machine learning model from invalid inputs (like requesting a negative forecast horizon) that would cause execution failures.
- **Why it was written this way**: Uses Pydantic's field constraints (e.g., `Field(gt=0, le=365)`) to enforce rules directly in the schema layer.
- **Interview explanation**: "The forecast schemas validate input parameters directly at the API boundary—such as checking that the requested horizon is a positive integer. This prevents malformed requests from reaching our ML engines."
- **Concepts used**: Constraint validation, DTO patterns.
- **Common interview questions**: *"Why validate fields at the API schema layer instead of inside the core business logic?"* (Validating early at the schema boundary allows us to return a `422 Unprocessable Entity` status immediately, saving compute resources and keeping our core code clean).
