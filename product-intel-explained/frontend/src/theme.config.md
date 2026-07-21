# Theme Configuration System (`frontend/src/theme.config.ts`)

This configuration system manages design tokens and styling themes for the app.

- **What it does**: Declares color schemes, typography, layout dimensions, border radius parameters, and custom shadows.
- **Why it exists**: Consolidates design parameters into a single source of truth, ensuring visual consistency across components.
- **Why it was written this way**: Implemented using a TypeScript configuration object, allowing editor autocomplete and static checks.
- **Interview explanation**: "This file defines our global design tokens. I structured it as a static TypeScript configuration to enforce consistency across pages, making it easy to tweak colors or branding elements in a single location."
- **Concepts used**: Design systems, styling tokens.
- **Common interview questions**: *"What are the benefits of using a design token configuration system over raw CSS variables?"* (It provides a single source of truth, supports editor autocomplete and type checking, and simplifies theme swaps).
