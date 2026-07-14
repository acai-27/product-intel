# ProductIntel

ProductIntel is a reduced-scope business intelligence service with five target engines plus a LangGraph orchestrator.

## Final Architecture

- Agentic Orchestrator: `src/core/agent/graph.py`
- NL2SQL Data Lookup: `src/core/nl2sql/`
- Forecast + Explain: `src/core/forecaster.py`, `src/core/explainer.py`
- Scenario Simulation: `src/core/simulator.py`
- Anomaly Scan: `src/core/new_anomaly/`

Removed scope: history search/RAG, experiment report embeddings, decision intelligence, optimizer, sensitivity, analytics module, standalone trend engine, legacy anomaly engine, and root-cause/hypothesis chains.

## API Surface

The backend keeps these FastAPI routers under `/api/v1`:

- `/forecast/*`
- `/explanation/*`
- `/scenario/*`
- `/anomaly/*`
- `/agent/*`

## Data And Models

- Forecasting and simulation use trained LightGBM artifacts in `models/` and product performance data from the configured database or `temporal_dataset.csv` fallback.
- NL2SQL is restricted to the narrowed allowlisted schema.
- Anomaly scan uses the canonical Isolation Forest implementation in `src/core/new_anomaly/` and reads `temporal_dataset.csv` by default.

## Local Verification

Use the permanent project interpreter:

```powershell
& 'C:\PythonEnvs\product-intel\Scripts\python.exe' -m pytest tests\test_nl2sql\test_validator.py -q
& 'C:\PythonEnvs\product-intel\Scripts\python.exe' -m pytest tests\test_langgraph\test_graph_integration.py -q
& 'C:\PythonEnvs\product-intel\Scripts\python.exe' -m pytest tests\test_api\test_anomaly.py tests\test_api\test_endpoints.py tests\test_langgraph\test_anomaly_tool_safety.py -q
```

Frontend build requires `frontend/node_modules` to already exist. Do not install dependencies unless explicitly requested.