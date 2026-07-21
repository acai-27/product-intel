# Application Context Providers (`frontend/src/context/` & `ThemeContext.tsx`)

This directory houses our global state context providers.

- **What it does**: Manages global settings (like dark mode and themes) and makes them available to all components.
- **Why it exists**: Avoids prop-drilling by providing a clean, centralized way to share global state.
- **Important files**:
  - `ThemeContext.tsx`: Manages active themes and coordinates class toggles on the document root.
- **Interview explanation**: "We use React Context to manage global state like application themes. This lets any component toggle dark mode without needing to pass props down multiple levels."
- **Concepts used**: React context, prop-drilling prevention.
