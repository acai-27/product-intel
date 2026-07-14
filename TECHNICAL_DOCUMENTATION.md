# Technical Documentation

## Scope

The codebase is now aligned to the final five-engine ProductIntel architecture:

1. LangGraph Agentic Orchestrator
2. NL2SQL Data Lookup
3. Forecast + Explain
4. Scenario Simulation
5. Isolation Forest Anomaly Scan

History search/RAG, experiment reports, report embeddings, decision intelligence, optimizer, sensitivity, analytics modules, standalone trend analysis, and the legacy anomaly package are out of scope.

## Runtime Flow

```text
FastAPI startup
  -> create configured database metadata
  -> initialize forecaster, explainer, simulator
  -> initialize anomaly engine with temporal_dataset.csv
  -> initialize LLM client and NL2SQL engine
  -> compile LangGraph with final-scope engine registry

User/API request
  -> FastAPI router or /agent/query
  -> LangGraph intent classifier and DAG planner when conversational
  -> final-scope tool execution
  -> deterministic payload plus optional LLM synthesis
```

## Core Modules

- `src/api/main.py`: FastAPI app, lifespan, and router registration.
- `src/api/dependencies.py`: lazy app-state initialization for final engines.
- `src/core/agent/`: LangGraph orchestration, planner, validation, tool dispatch, and visualization builders.
- `src/core/nl2sql/`: guarded natural-language-to-SQL execution over the narrowed schema.
- `src/core/forecaster.py`: recursive LightGBM forecasts.
- `src/core/explainer.py`: SHAP-based forecast explanations.
- `src/core/simulator.py`: what-if scenario simulation.
- `src/core/new_anomaly/`: canonical Isolation Forest anomaly implementation.

## Configuration Notes

- Python execution should use `C:\PythonEnvs\product-intel\Scripts\python.exe`.
- The obsolete temporary environment under `AppData\Local\Temp\product-intel-envs` should not be used.
- Do not change dependencies or environments unless explicitly requested.

## Verification

Backend checks currently focus on compile, NL2SQL validation, LangGraph integration, API endpoint shape, and anomaly engine safety. Frontend build is pending local `node_modules` availability.