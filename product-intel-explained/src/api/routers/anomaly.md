# Anomaly Detection Router (`src/api/routers/anomaly.py`)

This router exposes endpoints to scan and inspect performance anomalies across products.

- **What it does**: Exposes endpoints to retrieve historical anomalies, scan recent metrics, and rank products by anomaly severity.
- **Why it exists**: Serves the anomaly detection pages of the React dashboard, pointing users directly to outliers and revenue leakage points.
- **Why it was written this way**: Maps endpoints to the `AnomalyDetectionEngineV2` singleton.
- **Execution flow**: 
  - GET `/anomalies/{product_id}`: calls `anomaly_engine.run_detection()`.
  - GET `/anomalies/{product_id}/scan`: calls `anomaly_engine.scan_anomalies()`.
  - GET `/anomalies/critical/products`: calls `anomaly_engine.get_top_products()`.
- **Dependencies**: `AnomalyDetectionEngineV2`, Pydantic models.
- **Inputs**: HTTP parameters: `product_id`, `kpi`, `lookback_days`, `target_date`.
- **Outputs**: Lists of anomalous data points, severity scores, and opportunity vs. risk flags.
- **Interview explanation**: "This router surfaces anomalies. It exposes endpoints to retrieve graph outliers, execute lookback scans, and rank products by severity scores."
- **Concepts used**: RESTful routing, input parameter validation.
- **Common interview questions**: *"How do you design a high-performance endpoint that ranks items based on dynamic calculations?"* (We cache base results, run scans asynchronously, or expose pre-computed tables rather than running complex stats loops on every request).
