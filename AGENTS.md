# AGENTS.md — PS 26249

PROJECT: Integrated Predictive Maintenance & Fleet Availability Platform (hackathon PS 26249).

All data is SYNTHETIC. Use generic aircraft names only. No real aircraft types, no weapons, no combat or operational planning functionality. Decision-support for maintenance only.

ENVIRONMENT: Native local development only. Use Python 3.11, Node.js 20+, npm, and locally installed PostgreSQL 16. Docker, containers, Docker Compose, and container orchestration are NOT used or required anywhere.

STACK:

* Backend: Python 3.11 + FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL
* Database driver: psycopg
* ML: pandas, NumPy, scikit-learn, LightGBM, SHAP, joblib
* No deep learning unless explicitly instructed by the plan
* Frontend: React + Vite + TypeScript + Tailwind + ECharts
* Task runner: `scripts/tasks.py`
* Local model artifacts: `models/`
* Synthetic data: `data_gen/`

SOURCE OF TRUTH:

* `docs/plan.md` is the master implementation plan.
* Section numbers in `docs/plan.md` must not be renumbered.
* Implement the phases in order: Phase 0 → Phase 1 → ... → Phase 11.
* Do not skip ahead or implement future phases unless explicitly instructed.
* Follow the architecture, technology choices, data strategy, ML strategy, repository structure, API design, testing strategy, and demo flow defined in `docs/plan.md`.

RULES FOR EVERY TASK:

1. Inspect the existing repository before changing anything.

   * Summarise what already exists.
   * Read `AGENTS.md` and the relevant sections of `docs/plan.md`.

2. Write a short implementation plan before making large changes.

   * The plan must correspond to the current phase.
   * Do not begin large implementation work until the plan has been reviewed and approved.

3. Implement ONLY the current phase.

   * Do not implement future phases.
   * Do not create speculative features.
   * Do not add stubs for future functionality unless the current phase explicitly requires them.

4. Preserve existing functionality.

   * Do not unnecessarily rewrite or delete working code.
   * Run existing tests before and after significant changes when applicable.

5. Follow the technology and architecture specified in `docs/plan.md`.

   * Do not substitute frameworks, databases, ML libraries, or architectural patterns without explicit approval.
   * Do not introduce Docker or container tooling.

6. Keep all project data synthetic.

   * Use generic aircraft/component/system names.
   * Do not introduce real aircraft types, real fleet numbers, weapons, combat functionality, or operational mission-planning functionality.
   * Clearly label synthetic data in the application and documentation.

7. Keep the ML implementation honest.

   * Do not use `simulation_truth` as an ML feature.
   * Do not claim model accuracy on real aircraft or real operational data.
   * Report evaluation results as results on synthetic data.
   * Follow the model strategy specified in `docs/plan.md`.

8. Keep code maintainable.

   * Use clear names.
   * Keep functions reasonably small.
   * Use type hints where appropriate.
   * Document non-obvious logic.
   * Do not put secrets or credentials in source code.
   * Keep configuration in environment variables where specified by the plan.

9. Run appropriate validation.

   * Run tests.
   * Run linting.
   * Run frontend builds where applicable.
   * Run database migration checks where applicable.
   * Fix failures before considering the phase complete.

10. Respect the current phase boundaries.

    * Phase 0: repository/local environment skeleton only.
    * Phase 1: database models and migrations.
    * Phase 2: synthetic data generation.
    * Phase 3: backend APIs/auth/ingestion.
    * Phase 4: ML pipeline.
    * Phase 5: predictive maintenance engine/advisories/alerts.
    * Phase 6: fleet availability engine and scenarios.
    * Phase 7: digital twin.
    * Phase 8: frontend dashboard.
    * Phase 9: integration and polish.
    * Phase 10: testing and validation.
    * Phase 11: demo and local deployment.

11. Use one Git branch per phase.

    * Example: `phase-0-repository-environment`
    * Example: `phase-1-data-model`
    * Review the diff before merging.
    * Merge only after the phase acceptance criteria are satisfied.
    * Tag completed phases as specified by the workflow.

12. Work in a fresh Antigravity agent session for each phase.

    * Start each phase by reading `AGENTS.md`, `docs/plan.md`, and the existing repository.
    * Do not assume context from a previous agent session.

13. Be cautious with terminal commands.

    * Explain commands that modify the database, delete files, alter Git history, or perform other potentially destructive operations before running them.
    * Do not execute destructive commands without explicit approval.

14. When the task is complete, report:

    * Files created.
    * Files modified.
    * Files deleted, if any.
    * Commands executed.
    * Tests/checks executed.
    * Test/build/lint results.
    * Known gaps or remaining issues.

15. STOP after completing the requested phase/task.

    * Do not automatically continue into the next phase.
    * Do not add unrelated improvements.

SECURITY / SCOPE:

* This is a maintenance decision-support system.
* Keep functionality limited to maintenance, fleet availability, spares, health monitoring, planning, and related decision support described in `docs/plan.md`.
* Do not add combat, weapons, targeting, mission planning, or operational military functionality.

FINAL PRINCIPLE:

Follow `docs/plan.md` as the authoritative implementation plan and `AGENTS.md` as the persistent execution rules. When there is uncertainty, inspect the relevant section of `docs/plan.md` before making an implementation decision.
