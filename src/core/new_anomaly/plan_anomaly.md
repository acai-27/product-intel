# Anomaly Engine Migration Blueprint

This document details the complete integration plan for replacing the existing `src/core/anomaly` engine with the newly developed `anomaly_detect` module. It serves as a comprehensive guide for a backend or full-stack engineer to execute the migration safely without redesigning the UI.

---

## 1. Current State Analysis

**Backend Modules (`src/core/anomaly/`):**
- `engine.py`: Orchestrates all anomaly logic
- `residual.py`: Statistical residual anomaly detection
- `rolling.py`: Rolling trend detection
- `changepoint.py`: Change point detection
- `multivariate.py`: Multivariate anomaly detection
- `rules.py`: Business rule engine
- `relations.py`: KPI relationship monitoring
- `explain.py`: Anomaly explanation generation (SHAP)
- `severity.py`: Severity scoring
- `impact.py`: Business impact estimation
- `history.py`: Historical context calculations
- `ranking.py`: Product anomaly ranker

**APIs & Routes (`src/api/routers/anomaly.py`):**
- `/detect`, `/product`: Primary detection endpoints
- `/category`: Category-level rollups
- `/history`, `/root-cause`, `/change-point`, `/business-impact`, `/explain`: Sub-feature endpoints
- `/top-products`: Global product ranking

**Schemas (`src/api/schemas/anomaly.py`):**
- `AnomalyRequest`, `CategoryAnomalyRequest`, `GlobalAnomalyRequest`
- `AnomalyResponse` (Huge payload with residuals, expected vs actual, shap drivers, relations)
- `CategoryAnomalyResponse`, `GlobalRankingResponse`

**Frontend Context (`frontend/src/`):**
- **Services**: `recommendations.service.ts` calls `/anomaly/top-products` and `/anomaly/detect`.
- **Hooks**: `useRecommendations.ts` (`useTopAnomalies`, `useAnomalyDetails`)
- **Pages**: `RecommendationsPage.tsx` heavily relies on `expected_value`, `actual_value`, `percentage_change`, `severity_score`, `status` (Critical, High, Medium, Low), and `explanation.top_drivers` to render the Anomaly Detail Card.

---

## 2. Gap Analysis

| Existing Capability | New `anomaly_detect` Engine | Action |
| --- | --- | --- |
| Residual Detection | Isolation Forest with temporal context | **Replace** |
| Severity Scoring (0-100) | Normalized Anomaly Score (0-100) | **Replace** |
| Percentage Change | `deviation_pct` vs rolling mean | **Replace** |
| Status (Critical, High, Medium) | Status (Attention Required, Opportunity) | **Replace** |
| Explainability (SHAP top drivers) | Explainability via percentile threshold text | **Rewrite** (Frontend presentation changes) |
| Global Ranking (`/top-products`) | *Not supported out-of-the-box by single product POC* | **Rewrite** (Will require a wrapper service looping over products, or aggregating scores) |
| Category Anomalies | *Unsupported* | **Remove / Rewrite** |
| Change Point Detection | *Unsupported* | **Remove** |
| Relationship Monitoring | *Unsupported* | **Remove** |
| Business Impact Estimation | *Unsupported* | **Remove** |

---

## 3. Backend Migration Plan

- **`src/core/anomaly/*`**: All files in this directory will become obsolete.
- **`src/core/anomaly/engine.py`**: Rewrite the `AnomalyDetectionEngine` wrapper to inject `anomaly_detect.service.detect_anomalies`. The engine will no longer run the vast pipeline of sub-detectors.
- **`src/api/dependencies.py`**: Update `get_anomaly_engine` to instantiate the new simplified engine.
- **New Dependencies**: The backend will rely entirely on `anomaly_detect/` for core scoring logic. We will need to map `AnomalyResult` to the appropriate API responses.

---

## 4. Schema Migration Plan

**Current `AnomalyResponse`**: Massive 20+ field schema containing expected/actual values, residuals, shap drivers, change points, business rules, etc.

**Target Output Schema**: The new schema must reflect the POC outputs while ensuring the frontend has data to draw a chart.
- Add `AnomalySummaryResponse`
- Add `GraphDataPoint`
- Add `AnomalyPoint`

*See Section 9 for exact Data Contracts.*

---

## 5. API Migration Plan

- **Endpoints to Keep & Modify**:
  - `POST /anomaly/detect`: Rewritten to return the new `{summary, graph_data, anomalies}` schema.
  - `GET /anomaly/top-products`: Must be rewritten to aggregate the `AnomalyResult.summary.anomaly_count` and scores across the product catalog to return ranked risk products.
- **Endpoints to Remove**:
  - `/anomaly/history`
  - `/anomaly/root-cause`
  - `/anomaly/change-point`
  - `/anomaly/business-impact`
  - `/anomaly/explain`
  - `/anomaly/category`

*Goal: The API surface dramatically shrinks to just Detection and Global Ranking.*

---

## 6. Frontend Impact Analysis

**`RecommendationsPage.tsx`**:
- Currently expects a single `AnomalyResponse` payload. It maps `expected_value` vs `actual_value` for a specific day.
- **Change Required**: The page must now consume `anomalies` list and `graph_data`. The "Anomaly Detail Card" should be updated to show the *Summary Block* (Total anomalies, Positive Spikes, Negative Drops) instead of a single day's severity score.
- **Driver Explanations**: Remove the SHAP `top_drivers` progress bars. Replace them with the `Threshold Method: Percentile (Top 5%)` text explanation.
- **Top Products List**: Ensure the backend's rewritten `/top-products` continues to supply the sidebar list.

---

## 7. UI Compatibility Plan

**Constraint: UI styling must remain exactly as-is.**
- **Color mappings**:
  - Map `status = 'Attention Required'` to the existing `critical` or `danger` CSS classes (red colors).
  - Map `status = 'Opportunity'` to the existing `success` CSS classes (green colors).
- **Cards**: The structure of the detail cards stays the same, but the data binding changes. E.g., replace `percentage_change` with `deviation_pct`.
- **Top Drivers UI**: Instead of removing the block completely, reuse the container to render the `anomalies` table/grid.

---

## 8. Graph Integration Plan

The frontend will consume the newly exposed `graph_data` array to draw a comprehensive timeline context.
- **Line Chart**: Render a standard line chart (e.g., using Recharts/Chart.js if installed) mapping `date` on the X-axis and `value` on the Y-axis.
- **Anomaly Overlays**: Iterate through `graph_data`. Where `is_anomaly == true`, draw a scatter dot or marker on the line chart.
- **Color Coding Markers**:
  - Red markers for points where `anomaly_type == 'negative_drop'`
  - Green markers for points where `anomaly_type == 'positive_spike'`
- **Tooltips**: Hovering over a point displays `Value`, `Score (0-100)`, and `Deviation %`.

---

## 9. Data Contract Specification

The new JSON contract for `/anomaly/detect`:

```json
{
  "summary": {
    "total_points": 365,
    "anomaly_count": 18,
    "positive_anomalies": 10,
    "negative_anomalies": 8,
    "threshold_method": "percentile",
    "threshold_percentile": 95,
    "threshold_value": 82.4
  },
  "graph_data": [
    {
      "date": "2025-01-01",
      "value": 25000,
      "score": 12.5,
      "is_anomaly": false,
      "anomaly_type": null,
      "deviation_pct": null,
      "status": "Normal"
    }
  ],
  "anomalies": [
    {
      "date": "2025-06-15",
      "value": 5000,
      "score": 95.1,
      "is_anomaly": true,
      "anomaly_type": "negative_drop",
      "deviation_pct": -45.2,
      "status": "Attention Required"
    }
  ]
}
```

---

## 10. Migration Strategy

To ensure a safe rollout without breaking the frontend:
1. **Phase 1 (Backend Shadows)**: Create a parallel API route `POST /anomaly/v2/detect` returning the new contract utilizing `anomaly_detect`. Leave `v1` intact.
2. **Phase 2 (Global Ranking Aggregation)**: Implement a lightweight loop on the backend to power `/anomaly/v2/top-products` using the new engine.
3. **Phase 3 (Frontend Integration)**: Update `RecommendationsPage.tsx` to point to `/v2` endpoints. Map the new Graph Data into UI charts and map `Attention Required` / `Opportunity` statuses to existing CSS variables.
4. **Phase 4 (Validation)**: Verify that the UI renders identically in styling, but displays the new Isolation Forest output.
5. **Phase 5 (Cleanup)**: Cut over completely, deprecate `v1`, and remove old architecture.

---

## 11. Cleanup Plan

**Final Cleanup Checklist:**
- [ ] Delete `src/core/anomaly/` and all its Python files.
- [ ] Delete outdated DTOs in `src/api/schemas/anomaly.py`.
- [ ] Remove unused routes in `src/api/routers/anomaly.py` (`/root-cause`, `/explain`, etc.).
- [ ] Remove SHAP, Prophet, or heavy stats dependencies from `requirements.txt` if they were only used by the old anomaly engine.
- [ ] Remove obsolete frontend interfaces in `recommendations.service.ts`.
- [ ] Move `anomaly_detect` into `src/core/` to adhere to standard repo architecture.
