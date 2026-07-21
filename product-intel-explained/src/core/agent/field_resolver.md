# Field Resolver Utility (`src/core/agent/field_resolver.py`)

This file maps natural language terminology to strict schema properties.

- **What it does**: Resolves vague, conversational terms (e.g. 'ad budget', 'selling price', 'CTR') to database fields and model features (`marketing_spend`, `avg_selling_price`, `current_ctr`).
- **Why it exists**: Users use synonyms when querying data. The backend requires exact strings for dataframe lookups and model inputs.
- **Why it was written this way**: Implemented using a mapping dictionary and string similarity lookups.
- **Interview explanation**: "This file resolves synonyms to system-recognized column names. For example, it maps 'ad spend' to `marketing_spend`, ensuring the LLM doesn't break our data pipeline with unexpected field names."
- **Concepts used**: Token normalization, schema mapping.
