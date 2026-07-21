# Technical and Business Interview Questions Guide

This document prepares you for technical and business interviews based on the architecture and codebase of the AI Product Intelligence Platform.

---

## 1. System Architecture & Design Patterns

### Question: "How does the backend manage ML model weights to keep API latency low?"
* **Why the interviewer asks it:** Tests your understanding of memory management, server resources, and production ML deployment practices.
* **Ideal Answer:**  
  "We implement a Singleton state container pattern (`AppState` in `src/api/dependencies.py`). Instead of loading heavy LightGBM and SHAP TreeExplainer model files from disk on every API call, we use FastAPI's `lifespan` context manager to load and deserialize them into memory exactly once at server boot. Endpoints access these warmed-up instances via FastAPI dependency injection (`Depends`), ensuring sub-second response times."
* **Follow-up Questions:**  
  * *"Is your AppState container thread-safe?"* (Yes, since the models are read-only at inference time. If we were writing to them, we would need to implement threading locks).
  * *"What happens if a model file is missing or corrupt at startup?"* (The lifespan startup block fails, raising an exception and halting the server immediately. This is a deliberate 'Fail-Fast' design choice to avoid running a half-functional API).
* **Common Mistakes:**  
  * Suggesting that models are loaded dynamically on demand (which introduces huge latencies).
  * Saying models are loaded globally on file import (which blocks test suites and causes import loop errors).

---

## 2. Agentic Orchestration & LangGraph

### Question: "Why did you choose LangGraph instead of a standard linear LLM pipeline?"
* **Why the interviewer asks it:** Evaluates your understanding of stateful agent architectures, self-repair loops, and error-handling paradigms.
* **Ideal Answer:**  
  "We chose LangGraph because linear LLM chains are fragile and cannot handle errors or self-correction natively. In this application, a user query can lead to numerical calculations. We run a stateful loop: the agent plans a execution DAG, runs the tools, and a validator node checks the results against business rules. If validation fails (e.g., predicted profit exceeds revenue), the state machine routes the context back to a replanning node to correct parameters and recalculate."
* **Follow-up Questions:**  
  * *"How do you prevent the agent from getting stuck in an infinite loop?"* (We track a retry counter inside the `AgentState`. If it exceeds a limit, like 3 retries, the loop breaks and returns a fallback response).
  * *"How does the frontend display real-time updates as the graph executes?"* (We call `compiled_graph.stream()` inside our planner and stream status updates to the React client using Server-Sent Events).
* **Common Mistakes:**  
  * Saying "we used it because it is newer or trendier than standard chains".
  * Failing to explain *how* state is managed and how the validation-replanning cycle works.

---

## 3. Predictive Modeling & Time-Series

### Question: "How does your forecasting model predict 30 days ahead, and how did you prevent data leakage?"
* **Why the interviewer asks it:** Assesses your understanding of time-series data preparation, validation strategies, and data leakage risks.
* **Ideal Answer:**  
  "We train LightGBM models to forecast targets step-by-step using an autoregressive loop. The model predicts day $t+1$, appends it to the history, and uses the preprocessor to recalculate lag and rolling average features to predict day $t+2$. To prevent data leakage, we split our training, validation, and test datasets chronologically rather than randomly, ensuring the model never trains on future features to predict past values."
* **Follow-up Questions:**  
  * *"What is the main drawback of autoregressive models?"* (Error compounding: a small error on Day 1 is carried forward, increasing prediction variance over time).
  * *"How did you optimize preprocessing speed during the daily prediction loop?"* (We check if the input contains a single product. If so, we bypass expensive Pandas `groupby` operations with direct shifts, achieving a 100x speedup).
* **Common Mistakes:**  
  * Confusing time-series splits with standard k-fold cross-validation.
  * Forgetting that random shuffling leaks future data into the past.

---

## 4. Model Explainability & Trust

### Question: "Why use SHAP values instead of standard model feature importances?"
* **Why the interviewer asks it:** Tests your understanding of model explainability, game theory, and how to build trust with business users.
* **Ideal Answer:**  
  "Standard feature importance (like Gini importance in tree models) is calculated globally and suffers from correlation bias. SHAP values are based on coalitional game theory, calculating the exact marginal contribution of each feature for a specific prediction. This local attribution allows us to explain *why* sales will drop on a specific Tuesday, rather than just showing which features are important overall."
* **Follow-up Questions:**  
  * *"Is calculating SHAP values too slow for a live web API?"* (Yes, model-agnostic SHAP calculations are slow. We solve this by using `TreeExplainer` optimized for tree-based models and caching pre-calculated background samples to speed up calculations).
  * *"How do you display raw feature names to non-technical users?"* (We use a translation mapper to clean up raw features, showing 'Ad spend' instead of `marketing_spend_lag_7`).
* **Common Mistakes:**  
  * Confusing global feature importance with local, prediction-specific explanations.

---

## 5. Database & Infrastructure

### Question: "How do you handle connection drops when integrating with a serverless database like Neon?"
* **Why the interviewer asks it:** Tests your understanding of database connection pooling, network resilience, and serverless infrastructure challenges.
* **Ideal Answer:**  
  "Serverless databases like Neon pause compute nodes during idle periods to save costs, which drops active socket connections. To handle this, we configure our SQLAlchemy engine with `pool_pre_ping=True` to verify connection health before executing queries, and `pool_recycle=300` to recycle stale connections every 5 minutes."
* **Follow-up Questions:**  
  * *"How does the NL2SQL engine connect to the database?"* (It bypasses the ORM pool, using a direct, read-only `psycopg2` connection driver to run generated queries securely).
* **Common Mistakes:**  
  * Suggesting you open and close a new database connection on every query manually (which introduces massive latency).

---

## 6. Business Value & Scenario Simulation

### Question: "How does the Scenario Simulator translate to business value?"
* **Why the interviewer asks it:** Evaluates your ability to connect technical implementations to real-world business ROI.
* **Ideal Answer:**  
  "The simulator lets executives test business strategies (such as pricing or marketing adjustments) before committing budget. It runs a baseline forecast, then parses change requests (e.g. 'marketing +10%') to run a simulated forecast, and returns the absolute and percentage differences across all KPIs. This de-risks decision-making by quantifying the expected ROI of proposed changes."
* **Follow-up Questions:**  
  * *"How do you handle unrealistic scenario boundaries?"* (We enforce logical bounds directly in the simulator, like capping discounts at 100% and marketing spend at 0, keeping the simulation realistic).
* **Common Mistakes:**  
  * Focus too much on code details (like the regex parser) rather than discussing business ROI.
