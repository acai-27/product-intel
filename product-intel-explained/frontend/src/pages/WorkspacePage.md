# Workspace Chat Page View (`frontend/src/pages/WorkspacePage.tsx`)

This page component provides an interactive chat interface.

- **What it does**: Serves as an interactive workspace where users can query the agent, view execution progress, and inspect generated charts.
- **Why it exists**: Exposes the conversational agent to the user, allowing them to ask questions and view real-time calculations.
- **Why it was written this way**: Subscribes to the backend's EventSource stream and maps events (like charts, text, progress updates) to interactive components.
- **Interview explanation**: "This is the interactive chat workspace. It connects to our Server-Sent Events endpoint, displaying status updates (such as 'running simulator') and rendering charts as soon as they are yielded."
- **Concepts used**: EventSource streaming, state reconciliation, real-time updates.
- **Common interview questions**: *"How do you handle client-side rendering for continuous data streams?"* (We set up an EventSource listener, update the message history array incrementally as chunks arrive, and trigger re-renders to show status changes).
