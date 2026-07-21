# App Component Routing (`frontend/src/App.tsx`)

This component coordinates page routing and sets up context providers.

- **What it does**: Enforces layouts, wraps routes in context providers (like filters and themes), and routes views to pages (like Dashboard or Predictions).
- **Why it exists**: Serves as the root component for our React interface.
- **Why it was written this way**: Implemented using React Router to configure client-side navigation.
- **Interview explanation**: "This is the root component of the app. It sets up our global context providers and configures page routing for our analytics views."
- **Concepts used**: React context, client-side routing.
