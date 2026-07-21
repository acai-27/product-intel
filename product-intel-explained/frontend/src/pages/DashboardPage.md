# Dashboard Page View (`frontend/src/pages/DashboardPage.tsx`)

This page component serves as the primary analytics dashboard.

- **What it does**: Displays overall performance metrics (revenue, profit, sales volumes) and anomaly lists for selected products.
- **Why it exists**: Provides an initial snapshot of system performance and highlights outliers that need attention.
- **Why it was written this way**: Uses React lifecycle hooks to fetch data from `dashboard.service.ts` when dependencies change.
- **Interview explanation**: "The Dashboard page provides a high-level view of our performance logs. It renders historical trend lines and maps raw metrics to visual KPI cards."
- **Concepts used**: React hooks (`useEffect`, `useState`), data visualization integration.
