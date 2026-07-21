# Explainer Schemas (`src/api/schemas/explanation.py`)

This file defines data schemas for explainability request and response payloads.

- **What it does**: Defines inputs (like product ID and date) and outputs (like driver lists and SHAP values) for the explanation endpoints.
- **Why it exists**: Enforces a consistent API contract for explainability features, ensuring that driver metrics are returned in a structured format.
- **Why it was written this way**: Implemented using Pydantic schema constraints.
- **Interview explanation**: "This file defines input and output contracts for explainability endpoints, ensuring that SHAP drivers and natural language summaries are returned in a structured, verified format."
- **Concepts used**: Data contract definition, validation schemas.
