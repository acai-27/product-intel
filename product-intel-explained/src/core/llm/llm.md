# LLM Interface Layer (`src/core/llm/`)

This directory manages connection clients to our Large Language Models.

- **What it does**: Establishes API connections to LLM providers (NVIDIA NIM, Ollama) and handles retries, timeouts, and fallback options.
- **Why it exists**: Provides a unified interface for model calls, ensuring LLM clients share the same configuration parameters.
- **Important files**: `client.py` (manages connections, failovers, and JSON extraction).
- **Interview explanation**: "This module handles all external LLM API calls. I built a failover system in `client.py` that defaults to a local Ollama instance if the primary cloud service suffers a network timeout or API error."
- **Concepts used**: Provider fallback patterns, client configuration.
