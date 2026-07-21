# Execution Bootstrapper (`run.py`)

This file acts as the manual execution entry point for the FastAPI server.

- **What it does**: Invokes Uvicorn programmatically to run the app.
- **Why it exists**: Provides a simple command (`python run.py`) to launch the local development server with hot-reload enabled.
- **Why it was written this way**: Configured with `reload=True` for development, and binds to localhost (`127.0.0.1`) on port `8000`.
- **Execution flow**: Entry check `__name__ == "__main__"` -> Uvicorn calls `src.api.main:app` -> mounts lifespan context -> starts listening for HTTP queries.
- **Dependencies**: `uvicorn`, `src.api.main`.
- **Inputs**: CLI execution.
- **Outputs**: Local server listening on port 8000.
- **Interview explanation**: "The `run.py` script serves as our local development entry point, launching the Uvicorn ASGI server with hot-reloading turned on for high developer velocity."
- **Concepts used**: ASGI servers, entry point guards.
- **Examples**: `python run.py`.
- **Common interview questions**: *"Why use Uvicorn instead of run-on-import or standard WSGI?"* (WSGI is synchronous. FastAPI is built on ASGI/Uvicorn to handle asynchronous events, SSE connections, and WebSockets natively).
