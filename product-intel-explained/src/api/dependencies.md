# Global State Injection (`src/api/dependencies.py`)

This file is responsible for managing the cached machine learning model instances and database connections.

- **What it does**: Initializes, caches, and exposes the predictive and explainability engines to route controllers.
- **Why it exists**: Machine learning models and datasets are heavy. Initializing them on every API request is a performance bottleneck. This file manages them in memory.
- **Why it was written this way**: Implemented using an `AppState` class namespace that holds static cached references.
- **Execution flow**: 
  1. Router calls `Depends(get_forecaster)`.
  2. Getter method checks `AppState.forecaster`.
  3. If uninitialized, triggers lazy configuration via `load_app_state()`.
  4. Returns the cached instance.
- **Dependencies**: `ProductForecaster`, `PredictionExplainer`, `ScenarioSimulator`, database drivers, Pandas.
- **Inputs**: Configuration properties.
- **Outputs**: Cached engine singletons.
- **Interview explanation**: "This file implements our state container. We use the class-level Singleton pattern (`AppState`) to cache model weights in memory. Route controllers fetch engines via FastAPI dependency injection (`Depends`), decoupling the routing layer from the models."
- **Concepts used**: Singleton pattern, lazy initialization, dependency injection.
- **Examples**: Running SQLite database queries falling back to local CSV files if Neon is unreachable.
- **Common interview questions**: *"How do you design a database query fallback pattern inside dependency injectors?"* (We check env profiles and connections, dynamically executing PG, SQLite, or CSV lookups in a try-except block).
