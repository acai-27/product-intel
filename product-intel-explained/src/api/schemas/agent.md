# Agent Schemas (`src/api/schemas/agent.py`)

This file defines data validation models for agent endpoints.

- **What it does**: Enforces type checks and data constraints on incoming requests to the agent endpoint.
- **Why it exists**: Prevents malformed queries from entering the agent orchestrator.
- **Why it was written this way**: Implemented using Pydantic's `BaseModel`.
- **Inputs**: HTTP POST requests.
- **Outputs**: Instantiated validation structures.
- **Interview explanation**: "This file uses Pydantic's `BaseModel` to validate inputs to our agent endpoints. For example, it ensures the user's question is passed as a valid string before the query is routed to our LangGraph state machine."
- **Concepts used**: Data contract enforcement, static schema validation.
