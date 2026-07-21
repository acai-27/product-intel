# Anomaly Schemas (`src/api/schemas/anomaly.py`)

This file defines data structures for anomaly detection responses.

- **What it does**: Formats anomaly detection results, including details like dates, anomaly scores, and classification labels (e.g. Risk, Opportunity).
- **Why it exists**: Standardizes the API responses from our anomaly engine, ensuring a consistent contract with the frontend.
- **Why it was written this way**: Uses Pydantic's nested models to represent complex, nested JSON objects cleanly.
- **Interview explanation**: "This schema defines our anomaly detection payload contracts. It validates fields like severity scores, deviation percentages, and risk classifications to ensure the React UI receives structured, predictable data."
- **Concepts used**: Object nesting, serialization.
