# Utility & Helper Scripts (`src/utils/`)

This directory houses system logging, error tracking, and database seed configurations.

- **What it does**: Provides helper utilities for logging, evaluation metrics, and database seeding.
- **Why it exists**: Prevents code duplication by sharing common helper classes across our API and ML layers.
- **Important files**:
  - `logger.py`: Standardizes logging levels and trace formatting.
  - `metrics.py`: Computes model evaluation metrics (MAE, RMSE, R-squared).
  - `seed_db.py`: Feeds raw data records into our SQL tables.
- **Interview explanation**: "This directory consolidates helper utilities—like standardized logging, ML validation metrics, and database seed scripts—used across both our API and ML engines."
- **Concepts used**: Logging levels, evaluation metrics, database seeding.
