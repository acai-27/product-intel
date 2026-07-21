# Data Engineering Concepts

This document explains the key data engineering concepts used in the preprocessor and database layers.

---

## 1. Time-Series Pre-processing (Lags & Rolling Windows)
* **Definition:** Creating history-dependent variables (lags represent past values; rolling windows represent moving averages over a specific time window).
* **Why it is used here:** `TimeSeriesPreprocessor` builds lag features and rolling statistics (mean, std, min, max) for LightGBM.
* **Repository example:** 
  `src/pipeline/preprocessor.py` shifting and rolling dataframe columns.
* **Simple example:** 
  Calculating your average steps over the last 7 days to predict steps tomorrow.
* **Interview explanation:** "Our preprocessor generates lag and rolling window features to capture temporal patterns. For example, it creates 7-day and 30-day moving averages of revenue, allowing LightGBM to identify trends and volatility."
* **Common interview questions:** *"Why is standard dataset shuffling dangerous in time-series preprocessing?"* (It leaks future data into the past, causing data leakage and overly optimistic model validation scores).

---

## 2. Serverless Database Connection Pool Tuning
* **Definition:** Managing database connection lifecycles by recycling connections and checking health before querying.
* **Why it is used here:** SQLAlchemy is configured with `pool_pre_ping=True` and `pool_recycle=300`.
* **Repository example:** 
  Engine keywords configuration in `src/core/database.py`.
* **Simple example:** 
  Checking if a phone line is active before dialing out.
* **Interview explanation:** "Neon is a serverless database that pauses during idle times, dropping active socket connections. Enabling `pool_pre_ping` forces SQLAlchemy to verify connections before executing queries, and `pool_recycle=300` refreshes stale connections every 5 minutes."
* **Common interview questions:** *"What is connection pooling and why do we tune it?"* (It reuses active database connection sockets instead of opening new sockets for every query. We tune it to handle cold starts and dropped connections).

---

## 3. Train-Serve Skew Prevention
* **Definition:** Ensuring that data preprocessing rules applied during training match the preprocessing rules applied during real-time inference exactly.
* **Why it is used here:** Saving `TimeSeriesPreprocessor` as a serialized `.joblib` file and loading it at runtime.
* **Repository example:** 
  Saving preprocessor in `trainer.py` and loading it in `forecaster.py`.
* **Interview explanation:** "To prevent train-serve skew, we save the `TimeSeriesPreprocessor` instance as a joblib file during training. This saves its state—such as categorical index mappings—so the live API preprocesses new requests using the exact same rules."
* **Common interview questions:** *"Give an example of train-serve skew."* (If the training pipeline maps 'category_A' to index 0, but the live server maps it to index 1 due to dynamic category loading, the model's predictions will be completely wrong).
