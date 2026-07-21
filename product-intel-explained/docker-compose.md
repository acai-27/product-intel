# Docker Compose Configuration (`docker-compose.yml`)

This file orchestrates local multi-container services.

- **What it does**: Declares services, networks, ports, and environment variables needed to stand up the local environment.
- **Why it exists**: Allows developers to spin up the entire application stack (API backend, database configs, local volumes) using a single command.
- **Why it was written this way**: Maps external port 8000 to internal container port 8000, mounts local volume paths to hot-reload code updates, and injects environment configurations.
- **Dependencies**: Docker Compose runner.
- **Inputs**: `.env` configurations.
- **Outputs**: Running local multi-container system.
- **Interview explanation**: "The `docker-compose.yml` file acts as the configuration hub for our local development setup, linking the FastAPI backend with database environment flags, and mounting local paths to enable hot-reloading."
- **Concepts used**: Multi-container orchestration, volume mounting, port forwarding.
- **Common interview questions**: *"How do you handle environment variables and secrets in docker-compose?"* (We map environment keys to local `.env` files that are ignored by git, ensuring keys are never checked into version control).
