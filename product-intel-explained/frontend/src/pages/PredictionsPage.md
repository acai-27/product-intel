# Predictions Page View (`frontend/src/pages/PredictionsPage.tsx`)

This page component displays time-series forecasts and confidence bounds.

- **What it does**: Displays forecasted performance lines and shaded uncertainty bounds, and links to SHAP driver explanations.
- **Why it exists**: Helps users inspect predictions and understand the primary drivers behind the forecast.
- **Why it was written this way**: Integrates area charts to draw confidence intervals, and uses interactive elements to show SHAP drivers for selected dates.
- **Interview explanation**: "This page handles forecast inspections. It draws predictions alongside shaded confidence areas, and displays SHAP contributions for selected dates so users understand the drivers behind the numbers."
- **Concepts used**: Time-series charts, area rendering, interactive events.
