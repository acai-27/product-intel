# UI Chart Visualization Builder (`src/core/agent/visualization/`)

This directory builds interactive visualizations from raw analytical data.

- **What it does**: Translates model dataframes and database arrays into structured visualization JSON payloads (like lines, bars, and scatter configs).
- **Why it exists**: Conveys complex data trends visually through charts (like Recharts) on the React dashboard.
- **Important files**: `builder.py` (constructs structures), `generator.py` (determines metrics to plot), `planner.py` (decides chart types).
- **Interview explanation**: "This module converts raw table predictions and database records into structured visualization payloads, letting the frontend automatically render interactive charts."
- **Concepts used**: Visualization schemas.
