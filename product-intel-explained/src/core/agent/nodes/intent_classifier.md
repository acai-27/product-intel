# Intent Classification Node (`src/core/agent/nodes/intent_classifier.py`)

This node determines the type of user query.

- **What it does**: Classifies the query into categories like casual conversation, raw data lookup, forecasting, or scenario simulation.
- **Why it exists**: Routes queries to the appropriate processing path, bypassing complex calculations for simple questions.
- **Interview explanation**: "This node determines the query's intent (e.g. conversational vs. analytical) to route it through the correct path in our LangGraph."
- **Concepts used**: Few-shot classification, intent parsing.
