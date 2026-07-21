# Docker Configurations (`Dockerfile` & `docker-compose.yml`)

#These files manage containerization for the microservice.

# - **What it does**: `Dockerfile` defines instructions to build a container image. `docker-compose.yml` orchestrates the local stack.
# - **Why it exists**: Eliminates "works on my machine" issues by packaging the application with all OS-level system libraries needed for ML math operations.
# - **Why it was written this way**: Uses a multi-stage or python-slim base image to reduce footprint, installs requirements, exposes port 8000, and boots via Uvicorn.
# - **Execution flow**: Docker daemon runs instructions step-by-step to compile layers -> starts runtime container.
# - **Dependencies**: Docker runtime engine.
# - **Inputs**: Source code files, system configurations.
# - **Outputs**: Containerized microservice.
# - **Interview explanation**: "We use Docker configurations to package our FastAPI service with its underlying system libraries. This ensures that linear algebra dependencies required by LightGBM work identically in dev, staging, and production environments."
# - **Concepts used**: Containerization, multi-stage builds.
# - **Common interview questions**: *"How do you optimize Docker image size for Python ML workloads?"* (Use python-slim/alpine base images, combine RUN commands to reduce layers, copy only production dependencies, and exclude source cache artifacts).
