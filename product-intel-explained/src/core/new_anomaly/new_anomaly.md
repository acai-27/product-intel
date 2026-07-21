# Anomaly Engine Modules (`src/core/new_anomaly/`)

This directory houses the logic for our V2 anomaly detection engine.

- **What it does**: Implements automated scanning to flag deviations and anomalies in product performance data.
- **Why it exists**: Automatically highlights performance drops and viral trends for business users.
- **Important files**: 
  - `engine.py`: Coordinates scanning, evaluations, and product rankings.
  - `service.py`: Computes statistical flags using rolling thresholds.
  - `data_loader.py`: Handles data querying.
  - `threshold_calibrator.py`: Adjusts standard deviation bounds dynamically.
- **Interview explanation**: "This folder contains our V2 anomaly detection service. It calculates rolling standard deviations over a 180-day window, filters out noise dynamically, and calculates severity scores to rank products."
- **Concepts used**: Time-series outliers, dynamic thresholding.
