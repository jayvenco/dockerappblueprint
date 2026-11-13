# DockerAppBlueprint — CLAUDE.md

Self-hosted wizard that generates build prompts (and `CLAUDE.md`/`AGENTS.md`) for new Docker apps. Python 3.12, FastAPI, SQLAlchemy, Jinja2, vanilla JS, SQLite. Single container, data in `/app/data`.

## Layout
- `app/main.py` app + middleware (CSRF origin check, security headers), `app/routers/` (`pages` HTML, `api` REST v1, `ui` cookie-only settings endpoints)
- `app/services/wizard.py` wizard steps, defaults, improvements, follow-ups. Change questions HERE; UI and API follow.
- `app/services/promptgen.py` turns answers into the prompt text. The "rules for every app" live here.
- `app/services/{backup,logos,store}.py`, `app/security.py`, `app/deps.py`
- `app/static/` css (5 themes via `[data-theme]`), js (no inline scripts: CSP is `script-src 'self'`), bundled fonts
- `unraid/` templates + icon, `scripts/install-unraid.sh`, `docker/entrypoint.sh`

## Rules
- English everywhere (UI, docs, prompts). Keep it lightweight: avoid new dependencies.
- Default login `admin`/`admin` with forced change; never weaken that.
- Token (Bearer) endpoints live in `routers/api.py`; anything that manages tokens, keys or backups stays cookie-only in `routers/ui.py`.
- Update README, CHANGELOG, `AGENT_API.md` and screenshots with every user-visible change.
- Branches: `develop` (staging, image `:staging`) and `main` (production, `:latest`). Push to `develop`, ask the owner to approve, then promote to `main`.

## Commands
- Run: `docker compose up --build` (http://localhost:8834) or `./.venv/bin/uvicorn app.main:app --reload`
- Tests: `./.venv/bin/python -m pytest -q`
