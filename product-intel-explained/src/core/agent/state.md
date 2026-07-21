# Agent State Definition (`src/core/agent/state.py`)

This file defines the common state structure shared across LangGraph nodes.

- **What it does**: Declares the `AgentState` type (using TypedDict) which holds context like user queries, intent, execution plans, step results, and validation notes.
- **Why it exists**: Serves as the central state object passed between nodes in the LangGraph workflow.
- **Why it was written this way**: Inherits from Python's standard `TypedDict`, allowing type-checking of keys while maintaining compatibility with standard JSON operations.
- **Interview explanation**: "This file defines the shared state structure for our LangGraph. It acts as the database for the current query transaction, carrying variables like execution plans, raw engine outputs, and error notes through each node."
- **Concepts used**: TypedDict, state serialization.
