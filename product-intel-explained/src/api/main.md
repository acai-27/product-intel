# API Entrypoint (`src/api/main.py`)

This file mounts all routing layers, handles CORS middleware configurations, and manages application lifecycles.

- **What it does**: Serves as the central startup controller of the API microservice.
- **Why it exists**: Bootstraps the FastAPI framework, connects database layers, and registers sub-routers.
- **Why it was written this way**: Built with async lifespan handlers to warm up dependencies before accepting connections.
- **Execution flow**: 
  1. Boot sequence invokes `lifespan()`.
  2. Lifespan runs SQLAlchemy Base metadata table generation.
  3. Lifespan calls `load_app_state()` to load ML components.
  4. App registers routers, assets, and catch-all fallbacks.
- **Dependencies**: `FastAPI`, `CORSMiddleware`, SQLAlchemy Engine, `dependencies.py` loaders.
- **Inputs**: Incoming HTTP client socket requests.
- **Outputs**: Web endpoints, JSON responses, Server-Sent Events streams, served React UI pages.
- **Interview explanation**: "This file is our FastAPI entrypoint. I used the lifespan context manager to check database schemas and warm up our LightGBM model caches before we accept client traffic, preventing lag on initial requests."
- **Concepts used**: Lifecycle management, middlewares, Single Page Application routing fallbacks.
- **Examples**: Mounting static directory routes using `app.mount("/assets", ...)` allows React static chunks to serve alongside API requests.
- **Common interview questions**: *"How do lifespan contexts in FastAPI differ from old startup events?"* (Lifespan uses an async context manager, supporting clean setup *and* teardown code, unlike the old startup/shutdown event hooks).
