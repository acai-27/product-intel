# Application Entry Bootstrapper (`frontend/src/main.tsx`)

This script mounts the React application to the DOM.

- **What it does**: Renders the React root component into the DOM.
- **Why it exists**: The bootstrapper that starts the frontend application.
- **Why it was written this way**: Wraps the app in `React.StrictMode` during development to catch potential lifecycle bugs.
- **Interview explanation**: "This is the bootstrap file. It imports our CSS and renders the main `<App />` component into the DOM."
- **Concepts used**: DOM rendering, Strict Mode.
