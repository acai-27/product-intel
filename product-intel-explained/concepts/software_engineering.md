# Software Engineering Concepts

This document explains the key software engineering concepts used in the API and system layers.

---

## 1. Singleton Pattern (Memory Cache)
* **Definition:** A design pattern that restricts the instantiation of a class to a single object.
* **Why it is used here:** `AppState` caches database engines, forecasters, and SHAP explainers in memory.
* **Repository example:** 
  `src/api/dependencies.py`'s static namespace properties.
* **Interview explanation:** "We use the Singleton pattern via the `AppState` class namespace to cache model weights in memory. This prevents us from re-loading heavy model binaries on every HTTP request."
* **Common interview questions:** *"Is the Singleton pattern thread-safe in Python?"* (Not by default if multiple threads write to it. However, because our models are read-only at inference time, it is safe here).

---

## 2. Asynchronous I/O & Generators
* **Definition:** Non-blocking execution of input/output operations, and functions that yield values incrementally using `yield`.
* **Why it is used here:** FastAPI handles async requests; the agent streams responses using python generators.
* **Repository example:** 
  `process_query_stream()` in `src/core/agent/planner.py` using `yield`.
* **Interview explanation:** "We use asynchronous I/O and generators to implement Server-Sent Events. The agent streams status updates and chunked text to the client as they are generated, keeping the connection open without blocking other server worker threads."
* **Common interview questions:** *"How does python's yield keyword work under the hood?"* (It turns a function into a generator. Instead of returning a value and terminating, it pauses execution state and returns a value, resuming from that exact spot on the next call).

---

## 3. Server-Sent Events (SSE) Streaming
* **Definition:** An HTTP-based protocol allowing servers to push real-time updates to clients over a single HTTP connection.
* **Why it is used here:** FastAPI `StreamingResponse` pushes JSON-encoded status updates and visualization specifications to the UI.
* **Repository example:** 
  Endpoint `/agent/query` in `src/api/routers/agent.py`.
* **Interview explanation:** "I chose Server-Sent Events over WebSockets for query streaming. Since our agent only needs to push updates downstream to the client, SSE provides a lightweight, standard HTTP-based protocol without the overhead of bidirectional WebSockets."
* **Common interview questions:** *"What is the difference between SSE and WebSockets?"* (WebSockets are bidirectional and use a custom protocol. SSE is unidirectional (server-to-client) and uses standard HTTP).
