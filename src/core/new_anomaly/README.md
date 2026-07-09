# Anomaly Detection POC

## Purpose
This is a standalone module capable of identifying unusual KPI behavior for individual products. It employs Isolation Forest combined with temporal feature engineering to generate explainable anomaly points.

## Architecture & Folder Structure
```
anomaly_detect/
├── README.md                # Documentation
├── build_anomaly.py         # CLI entry point
├── models.py                # Dataclasses
├── data_loader.py           # Data extraction
├── feature_builder.py       # Temporal feature engineering
├── detector.py              # Isolation Forest logic
├── threshold_calibrator.py  # Anomaly score thresholding
├── service.py               # Main orchestration layer
├── utils.py                 # Shared helper functions
└── examples/
    └── sample_run.py        # Minimal usage example
```

## Execution Flow
1. **Load Data**: Extract history for a specific product and date range.
2. **Feature Engineering**: Generate temporal context features (lag, rolling mean/std).
3. **Train Model**: Fit Isolation Forest on the engineered features.
4. **Score Normalization**: Map raw model scores to a 0-100 business-friendly range.
5. **Threshold Calibration**: Apply KPI-specific percentile thresholds to flag anomalies.

## Feature Engineering Strategy
Temporal features provide the model awareness of local behavior, trends, and sudden shifts:
- `lag_1`: Value 1 day ago
- `lag_7`: Value 7 days ago
- `rolling_mean_7`: 7-day trailing average
- `rolling_std_7`: 7-day trailing standard deviation

## Isolation Forest Rationale
Isolation Forest isolates anomalies instead of profiling normal points. It's unsupervised, doesn't require labels, and works exceptionally well with skewed and non-Gaussian business KPI distributions, avoiding the pitfalls of purely statistical IQR or Z-score methods.

## Anomaly Score Methodology
- Isolation Forest internally uses path lengths.
- `score_samples()` returns normality scores (negative values where lower is more anomalous).
- Scores are inverted so that a higher value = more anomalous, and a lower value = more normal.
- Scores are normalized to a 0-100 business-friendly range.
- Top 5% highest anomaly scores are classified as anomalies.

Example:
If raw `score_samples()` returns -0.75 (anomalous) and -0.25 (normal):
1. Invert: 0.75 and 0.25
2. Normalize (assuming min/max boundaries align): 100 (anomalous) and 0 (normal)

## Threshold Calibration Rationale
We utilize a 95th percentile threshold across all KPIs, dynamically adapting to the volatility of each specific metric rather than using hardcoded score cutoffs.

## Explainability
An anomaly point flagged by this module can be explained as:
"This observation falls within the most extreme 5% of historical behavior for this KPI after evaluating the KPI value, recent history, and rolling statistics."

## Example Usage
```bash
python build_anomaly.py --product_id P001 --kpi revenue --date_range "180 Days"
```
