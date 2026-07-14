# ProductIntel Final Components

This note supersedes older component explanations that described history/RAG, experiment reports, decision intelligence, optimizer, sensitivity, analytics, and legacy anomaly modules.

## Active Components

- LangGraph orchestrator: classifies intent, plans final-scope DAGs, validates tool usage, executes tools, and streams synthesized responses.
- NL2SQL: answers factual product-performance lookup questions through guarded SQL.
- Forecast + Explain: produces KPI forecasts and SHAP driver explanations.
- Scenario Simulation: compares baseline forecasts with user-specified business changes.
- Anomaly Scan: detects and ranks product KPI anomalies using the canonical `src/core/new_anomaly/` Isolation Forest flow.

## Removed Components

The repository should not contain live code paths for historical repository search, report embeddings, experiments, AI scientist decisions, optimizer/sensitivity engines, analytics modules, root-cause chains, or duplicate anomaly packages.