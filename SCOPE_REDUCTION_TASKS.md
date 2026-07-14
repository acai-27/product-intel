# Scope Reduction Task Tracker

Target architecture: final reduced product-intel scope. Per the latest instruction, History Search / RAG is removed even though the PRD v3 docx still mentions it as live. Anything tied to `experiment_dataset.csv`, experiment reports, report embeddings, repository search, or historical intelligence retrieval is out of scope.

## Final Target Components

Use this as the canonical list. These are the only product capabilities that should remain:

1. Agentic Orchestrator: `src/core/agent/graph.py` and the LangGraph node pipeline.
2. NL2SQL Data Lookup: `src/core/nl2sql/`, with narrowed queryable schema.
3. Forecast + Explain: `src/core/forecaster.py` and `src/core/explainer.py`.
4. Scenario Simulation: `src/core/simulator.py`.
5. Anomaly Scan: `src/core/new_anomaly/` using Isolation Forest.

Removed from target scope:

- History Search / RAG / Historical Intelligence Repository.
- Anything using `experiment_dataset.csv` or experiment/report embeddings.
- Decision / AI-Scientist engine.
- Optimizer.
- Sensitivity / elasticity engine.
- Analytics modules and standalone trend engine.
- Legacy rule/residual anomaly engine.
- Automated root-cause / hypothesis chain.

## API Surface To Keep

Keep and align these routers only:

- `src/api/routers/agent.py`
- `src/api/routers/forecast.py`
- `src/api/routers/explanation.py`
- `src/api/routers/scenario.py`
- `src/api/routers/anomaly.py`

## Task Status

Status key: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`.

| ID | Status | Task | Notes |
| --- | --- | --- | --- |
| T01 | DONE | Identify canonical target components and active routers. | Target is orchestrator, NL2SQL, Forecast+Explain, Scenario Simulation, Anomaly Scan. |
| T02 | DONE | Remove RAG / Historical Intelligence Repository. | Removed history package/router/schema/tests, repository frontend artifacts, `history.zip`, and `experiment_dataset.csv`. |
| T03 | DONE | Remove experiment dataset dependencies. | Live-code audit is clean for `experiment_dataset.csv`, `Experiment`, `Report`, `ReportEmbedding`, `repository_search`, and `repository_extract`. |
| T04 | DONE | Remove Decision / AI-Scientist engine. | Decision core/router/schema/tests deleted; planner/registry/synthesizer no longer reference `decision_ask`. |
| T05 | DONE | Consolidate shared DB infrastructure. | Shared DB/model files are kept; experiment/report-only model references removed from live schema paths. |
| T06 | DONE | Make `load_app_state()` initialize only target components. | Startup now initializes forecaster, explainer, simulator, anomaly engine, LLM, NL2SQL, and LangGraph. |
| T07 | DONE | Remove legacy planner imports/routes for deleted engines. | `LLMPlannerAgent` is a final-scope compatibility wrapper and no longer imports optimizer/analyzer/analytics/sensitivity. |
| T08 | DONE | Narrow LangGraph capability registry. | Registry contains forecast, explanation, simulation, anomaly, and NL2SQL capabilities only. |
| T09 | DONE | Clean agent tool dispatchers. | Static audit confirms no live dispatcher references to repository, decision, optimizer, sensitivity, analytics, analysis, or legacy anomaly modules. |
| T10 | DONE | Clean agent prompts/templates/validator/synthesizer copy. | Removed stale RAG/decision/optimizer/root-cause copy from active agent flow. |
| T11 | DONE | Narrow NL2SQL schema. | Experiment/report tables are removed. `events`, `snapshots`, and `knowledge_base` remain allowlisted pending any future product decision to narrow further. |
| T12 | DONE | Remove optimizer, sensitivity, analytics, and analyzer engines. | Core modules, routers, schemas, and tests removed; frontend no longer calls `/analytics/*`. |
| T13 | DONE | Consolidate anomaly implementation. | Root `anomaly_detect/` duplicate removed; canonical engine uses `src/core/new_anomaly/` and `temporal_dataset.csv`. |
| T14 | DONE | Remove legacy anomaly engine if present. | `src/core/anomaly/` removed; API anomaly router points to `new_anomaly`. |
| T15 | DONE | Decide/delete `dep_graph/`. | Removed as non-runtime/out-of-scope cleanup artifact. |
| T16 | DONE | Align frontend to final API surface. | Removed deleted routes/pages/services and switched dashboard/predictions away from `/analytics/*` to forecast endpoints. |
| T17 | DONE | Update tests to final contracts. | Updated NL2SQL, LangGraph, anomaly, and endpoint tests for final response shapes. |
| T18 | DONE | Static reference audit. | `rg` over `src frontend tests` returns no live-code hits for removed engines/RAG references. |
| T19 | DONE | Syntax compile check. | `py_compile` passed for modified backend/test files. |
| T20 | DONE | Run focused backend tests. | NL2SQL, LangGraph, API endpoint, and anomaly safety slices passed. |
| T21 | BLOCKED | Run frontend build/lint after page/API cleanup. | `frontend/node_modules` is absent. No dependency install was performed per instruction. |
| T22 | DONE | Update docs to final no-RAG scope. | README, technical documentation, and component notes now describe final five-engine scope. |

## Verification Log

Passed with `C:\PythonEnvs\product-intel\Scripts\python.exe`:

```powershell
& 'C:\PythonEnvs\product-intel\Scripts\python.exe' -m py_compile <modified backend/test files>
& 'C:\PythonEnvs\product-intel\Scripts\python.exe' -m pytest tests\test_nl2sql\test_validator.py -q
& 'C:\PythonEnvs\product-intel\Scripts\python.exe' -m pytest tests\test_langgraph\test_graph_integration.py -q
& 'C:\PythonEnvs\product-intel\Scripts\python.exe' -m pytest tests\test_api\test_anomaly.py tests\test_api\test_endpoints.py tests\test_langgraph\test_anomaly_tool_safety.py -q
```

Frontend build/lint was not run because `frontend/node_modules` is missing and dependency installation was not requested.

## Open Decisions

- NL2SQL schema can be narrowed further to only `product_performance` if desired. Current final cleanup keeps `events`, `snapshots`, and `knowledge_base` because they are not experiment/report embedding tables.
- `/agent/query` remains SSE streaming as the active contract.