# Training Pipeline Modules (`src/pipeline/`)

This directory houses the logic for data generation, preprocessing, and model training.

- **What it does**: Cleans data, constructs features (like lags and moving averages), trains LightGBM models, and calculates empirical confidence parameters.
- **Why it exists**: Runs the heavy, offline training loop to compile model weights for production inference.
- **Important files**:
  - `preprocessor.py`: Implements the `TimeSeriesPreprocessor` class to construct features.
  - `trainer.py`: Controls model training, validation splits, and metadata serialization.
  - `data_generator.py`: Synthesizes mock performance logs for testing.
- **Interview explanation**: "This folder contains our offline ML pipeline. It handles chronological train/val splits, runs rolling feature engineering, trains LightGBM models, and saves the preprocessor configurations."
- **Concepts used**: Autoregressive preprocessing, model serialization, train-serve skew prevention.
