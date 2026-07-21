# LangGraph State Machine Definition (`src/core/agent/graph.py`)

This file compiles and coordinates the stateful AI agent graph.

- **What it does**: Directs user queries through intent classification, task planning, execution, output validation, and replanning stages.
- **Why it exists**: Coordinates agent nodes, allowing the AI to call tools, self-correct, and validate outputs.
- **Why it was written this way**: Implemented using a modular `StateGraph`. Each step outputs state updates that merge back into the main `AgentState`.
- **Execution flow**: 
  1. Entry node runs classification.
  2. Routes dynamically to fast summary or DAG planning.
  3. Executes the plan by calling the forecast or scenario engines.
  4. Validates outputs; cycles to replanner if errors are detected.
- **Dependencies**: `StateGraph`, `AgentState`, core engine nodes.
- **Inputs**: User query string.
- **Outputs**: Fully populated `AgentState` containing the final answer, charts, and execution logs.
- **Interview explanation**: "This file maps out our agent's execution graph. Using LangGraph, I built a state machine that parses intent, delegates calculations to deterministic tools, and validates outputs, allowing the agent to self-correct before responding."
- **Concepts used**: Stateful workflows, conditional routing, state machines.
- **Common interview questions**: *"What are the advantages of using a compiled graph over direct function calls?"* (It provides structured execution pathways, handles conditional loops natively, and maintains a clean state audit log across nodes).
