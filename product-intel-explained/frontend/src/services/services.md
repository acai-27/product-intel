# API Service Layer (`frontend/src/services/`)

This directory manages API calls to the backend.

- **What it does**: Handles HTTP requests and parses backend responses.
- **Why it exists**: Isolates network fetch operations from React components.
- **Important files**:
  - `dashboard.service.ts`: Queries metrics and historical analytics.
  - `predictions.service.ts`: Fetches forecasts and SHAP drivers.
  - `settings.service.ts`: Updates client configurations.
  - `workspace.service.ts`: Handles workspace actions.
- **Interview explanation**: "This folder contains our service layers. By isolating `fetch` requests here, we decouple components from backend URL paths, making it easy to swap in new APIs."
- **Concepts used**: Service layer pattern, network isolation.
