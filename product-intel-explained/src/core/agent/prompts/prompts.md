# Agent Prompt Definitions (`src/core/agent/prompts/`)

This directory houses instruction templates for the LLM.

- **What it does**: Declares the system prompts for intent classification (`intent_classifier_prompt.py`) and workflow planning (`planner_prompt.py`).
- **Why it exists**: Isolates complex prompt texts from Python execution files, making them easier to refine.
- **Interview explanation**: "We keep our system prompt templates isolated in this directory, separating prompt design from our core routing logic."
- **Concepts used**: Prompt templating.
