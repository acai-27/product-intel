# Agentic Orchestration Concepts

This document explains the key agentic orchestration concepts used in the platform's state machine.

---

## 1. Directed Acyclic Graph (DAG) Planning
* **Definition:** A structural planning model where execution steps are arranged in a flow containing directed edges and no feedback loops (cycles) until a task completes.
* **Why it is used here:** The LLM Planner converts a natural language question into a sequence of tool execution steps (e.g., Step 1: Forecast KPI, Step 2: Run SHAP Drivers).
* **Repository example:** 
  In `src/core/agent/nodes/dag_planner.py`, the LLM compiles the execution plan array containing task targets and parameters.
* **Simple example:** 
  A build tool (like Webpack or Make) analyzing code dependencies to compile files in the correct sequence.
* **Interview explanation:** "We use DAG planning to translate natural language queries into structured sequences of execution steps. This ensures that the agent runs tools in their correct dependency order, preventing execution failures."
* **Common interview questions:** *"Why use a DAG for tool orchestration instead of letting the LLM call tools dynamically?"* (Dynamic tool calling is prone to execution loops and resource waste. Planning a DAG beforehand ensures validation checks can be run on the plan before execution begins).

---

## 2. Stateful Agent Loop (Agent State)
* **Definition:** An architecture where the execution path is determined dynamically by querying and updating a persistent, shared state database across execution nodes.
* **Why it is used here:** A centralized state dictionary (`AgentState`) is updated sequentially by each node in our LangGraph state machine.
* **Repository example:** 
  `src/core/agent/state.py` defines the `AgentState` type using Python's `TypedDict`.
* **Simple example:** 
  A wizard form passing collected inputs step-by-step until the final checkout page.
* **Interview explanation:** "We implement a stateful agent loop. By keeping a centralized `AgentState` object, each node writes its output back to the state, and downstream nodes read from it to decide the next path."
* **Common interview questions:** *"How does stateful orchestration differ from a stateless chain?"* (Stateless chains pass data directly from function A to function B. Stateful orchestration maintains a shared context, allowing nodes to inspect previous steps, handle failures, and cycle back to prior states if necessary).

---

## 3. Agentic Self-Repair (Validation & Replanning)
* **Definition:** A design pattern where the agent checks outputs against business constraints and automatically generates correction steps if validation checks fail.
* **Why it is used here:** If the forecasting engine yields logical anomalies (such as negative conversion rates), the validator node routes the state back to the replanner to adjust parameters.
* **Repository example:** 
  Routing rules in `src/core/agent/graph.py` direct traffic from `validator` back to `replanner`.
* **Simple example:** 
  A form validation script highlighting incorrect fields and prompts the user to fix them before submitting.
* **Interview explanation:** "We implement agentic self-repair. If our validator node catches an illogical forecast value, the state machine routes the context back to a replanning node to adjust parameters and recalculate."
* **Common interview questions:** *"How do you prevent infinite loop conditions in self-repair loops?"* (We track a retry counter in the `AgentState` context, terminating the loop and returning a fallback response if the retry limit (e.g. 3) is exceeded).
