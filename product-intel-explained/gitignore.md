# Git Exclusion Configuration (`.gitignore`)

This file specifies untracked files that Git should ignore.

- **What it does**: Excludes compiled code, system artifacts, secrets, virtual environments, and heavy local database binaries from version control.
- **Why it exists**: Prevents commit pollution, secure keys leak, and large binary storage inside the Git history.
- **Why it was written this way**: Explicitly ignores directories like `__pycache__/`, `.venv/`, `.env`, and local database files like `data/test.db`.
- **Interview explanation**: "We use a customized `.gitignore` to protect environment variables and ignore temporary workspace directories like `__pycache__/`, ensuring only high-quality source code gets tracked."
- **Concepts used**: Git path tracking, glob patterns.
- **Common interview questions**: *"What happens if you commit a large binary or secret key by mistake? How do you fix it?"* (Simply adding it to `.gitignore` won't delete it from historical commits. You must rewrite the history using tools like `git-filter-repo` or BFG Repo-Cleaner to completely scrub the data).
