# UI Components Overview (`frontend/src/components/`)

This folder houses modular UI components for the analytics interface.

- **What it does**: Implements elements like filters, KPI cards, loading states, markdown engines, thinking loaders, and visualization panels.
- **Why it exists**: Promotes code reuse and keeps our page-level layouts clean.
- **Important files**:
  - `ChatVizPanel.tsx`: Instantiates charts in the chat sidebar based on visual payloads.
  - `DashboardKpiCards.tsx`: Draws KPI summary widgets with indicator flags.
  - `GlobalFilterBar.tsx` & `FilterContext.tsx`: Manages selections (dates, category scopes) globally.
  - `ThreeDInteractiveBackground.tsx`: Renders a background canvas.
  - `ThinkingIndicator.tsx`: Displays pulsing loaders during query execution.
  - `MarkdownBody.tsx`: Renders formatted textual logs.
- **Interview explanation**: "This folder consolidates our reusable UI components. By isolating things like KPI cards, chat sidebars, and thinking indicators, we can keep page layouts focused and update UI elements without breaking page logic."
- **Concepts used**: Reusable components, state containment.
