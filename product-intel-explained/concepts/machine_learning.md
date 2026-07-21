# Machine Learning Concepts

This document explains the key machine learning concepts used in the forecasting and explainability engines.

---

## 1. Autoregressive Time-Series Forecasting
* **Definition:** A time-series forecasting technique where tomorrow's prediction uses today's prediction as an input feature.
* **Why it is used here:** Standard regression models can only predict one step ahead. Autoregressive prediction allows them to forecast multi-day sequences by chaining inputs.
* **Repository example:** 
  The day loop in `src/core/forecaster.py` appends daily forecasts to the dataset to recalculate features for the next day.
* **Simple example:** 
  Forecasting weather by using tomorrow's predicted temperature to predict the day after.
* **Interview explanation:** "The forecaster uses an autoregressive loop with LightGBM. It predicts one day at a time, appends that prediction to the history, and recalculates features to predict the next day."
* **Common interview questions:** *"What is the main drawback of autoregressive models?"* (Error compounding: a small error on Day 1 is carried forward, increasing prediction variance over time).

---

## 2. Game-Theoretic Feature Attribution (SHAP)
* **Definition:** A method based on coalitional game theory that determines the marginal contribution of each feature to a prediction.
* **Why it is used here:** `PredictionExplainer` calculates driver contributions to explain specific daily forecasts.
* **Repository example:** 
  `src/core/explainer.py` using `shap.TreeExplainer` on the prediction features.
* **Simple example:** 
  Splitting credit for a team goal among players based on their marginal actions.
* **Interview explanation:** "We use SHAP values to calculate the marginal contribution of each feature. This gives us a mathematically sound attribution that avoids correlation bias, unlike simple model feature importance coefficients."
* **Common interview questions:** *"Why are Shapley values mathematically preferred over standard Gini feature importances?"* (Shapley values are locally consistent and satisfy efficiency, symmetry, and dummy axioms, preventing correlation bias).

---

## 3. Empirical Confidence Intervals
* **Definition:** Calculating prediction uncertainty intervals using historical error distributions rather than assuming theoretical gaussian curves.
* **Why it is used here:** `trainer.py` evaluates models on a test set to save step-by-step errors; `forecaster.py` applies these standard deviations at runtime.
* **Repository example:** 
  Metadata standard deviation application in `src/core/forecaster.py`.
* **Simple example:** 
  Predicting a commute time of 30 mins +/- 5 mins based on our actual commute logs.
* **Interview explanation:** "Instead of assuming a theoretical gaussian distribution, we calculate step-specific empirical bounds. We track how much the model's accuracy degrades at each forecast step (e.g. Day 1 vs Day 30) using offline validation data, and use these standard deviations to scale the confidence intervals dynamically."
* **Common interview questions:** *"Why do forecasting confidence intervals widen over time?"* (Because error propagates and compounds step-by-step in autoregressive models).
