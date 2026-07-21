# Agent Router (`src/api/routers/agent.py`)

This endpoint streams Server-Sent Events (SSE) representing the stateful agentic response.

- **What it does**: Directs natural language queries to the agent planning layer and returns a real-time streamed response.
- **Why it exists**: Provides the chatbot-like interactive experience on the frontend, feeding status updates, metadata, and visualization events.
- **Why it was written this way**: Utilizes FastAPI's `StreamingResponse` to process queries asynchronously, chunk by chunk, without locking the connection pool.
- **Execution flow**: 
  1. Frontend sends a query to `/agent/query`.
  2. Router fetches `LLMPlannerAgent` from dependency injection.
  3. Router returns a `StreamingResponse` wrapping `process_query_stream()`.
- **Dependencies**: `FastAPI`, `StreamingResponse`, `LLMPlannerAgent`.
- **Inputs**: `AgentQueryRequest` containing `query`.
- **Outputs**: `text/event-stream` chunks containing status messages, chart data, and the final synthesized answer.
- **Interview explanation**: "The agent router maps user queries to the LangGraph executor via a Server-Sent Events `StreamingResponse`. This yields a highly responsive UX by showing the agent's progress (e.g. 'planning calculations', 'running forecasting') in real-time."
- **Concepts used**: Server-Sent Events (SSE), asynchronous generators.
- **Common interview questions**: *"Why use StreamingResponse (SSE) over WebSockets?"* (WebSockets are bidirectional, adding state management complexity. SSE is a lightweight, unidirectional HTTP-based streaming protocol, which is ideal for LLM response streaming).
