# Capability & Data Registries (`src/core/agent/registry/`)

This directory defines capabilities and database schemas exposed to the LLM.

- **What it does**: Declares lists of analytical tools (`capability_registry.py`) and SQL schemas (`data_registry.py`) available to the agent.
- **Why it exists**: Serves as the agent's catalog, describing inputs and rules so the LLM knows how to call tools and generate correct database queries.
- **Interview explanation**: "The registries serve as the interface catalog for our agent, outlining available APIs, databases, and schemas so the LLM can plan and generate queries accurately."
- **Concepts used**: Metadata registries.
