# Agent Orchestration Compatibility Wrapper (`src/core/agent/planner.py`)

This file acts as a compatibility layer for the backend streaming interface.

- **What it does**: Orchestrates Server-Sent Event (SSE) responses by running queries through the LangGraph agent graph, and falls back to a deterministic, rule-based route if the graph crashes.
- **Why it exists**: Allows API endpoints to stream status updates and metrics seamlessly.
- **Why it was written this way**: Uses python generators (`yield`) to push updates as they occur, and includes a fallback router to guarantee high availability.
- **Execution flow**: 
  1. Frontend calls query stream.
  2. Planner triggers `compiled_graph.stream()`.
  3. Yields status events as nodes execute (e.g. 'planning', 'calculating').
  4. Yields metadata and visualization specs.
  5. If an exception occurs, falls back to a deterministic regex router to run calculations directly.
- **Dependencies**: `compiled_graph`, `LLMClient`, `TimeSeriesPreprocessor` parameters.
- **Inputs**: User query string.
- **Outputs**: Yielded SSE chunks.
- **Interview explanation**: "The planner wraps our LangGraph execution. It yields status updates to the client in real-time. If the LLM service suffers a timeout or connection failure, the planner falls back to a rule-based regex router to compute the forecast anyway, ensuring the app never goes down."
- **Concepts used**: Generator protocols, fallback routing, multi-threading queue drain.
- **Common interview questions**: *"How do you handle LLM outages in a production agent?"* (We implement deterministic fallback routes. If the agent graph fails due to an LLM exception, we parse the query using regex rules and execute the models directly).
