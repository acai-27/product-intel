# Requirements Configuration (`requirements.txt`)

This file manages Python dependencies for the microservice.

- **What it does**: Declares third-party packages required to build, test, run, and explain the machine learning models.
- **Why it exists**: Guarantees deterministic environments across developer machines, CI/CD runners, and Docker containers.
- **Why it was written this way**: Pins major or exact versions (e.g. `fastapi>=0.100.0`, `lightgbm>=4.0.0`) to balance compatibility fixes with dependency drift protection.
- **Dependencies**: None.
- **Inputs**: None.
- **Outputs**: None.
- **Interview explanation**: "The `requirements.txt` file pins the runtime dependencies of the microservice. It ensures we align FastAPI (for API routing), LangGraph (for stateful AI flow), LightGBM (for prediction), and SHAP (for explainability) across all execution hosts."
- **Concepts used**: Package management, semantic versioning.
- **Examples**: Running `pip install -r requirements.txt` reads this configuration and constructs the environment.
- **Common interview questions**: *"How do you handle dependency drift or security vulnerabilities in production Python services?"* (We pin exact versions and use security scanners like safety/dependabot, separating development and production requirements).
