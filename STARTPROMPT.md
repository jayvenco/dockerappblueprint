# DockerAppBlueprint — Start Prompt

Paste everything below the line into Claude Code, started in an empty `dockerappblueprint` folder.

---

You are building **DockerAppBlueprint**: a lightweight, self-hosted web app that guides me through a step-by-step wizard and outputs a ready-to-paste **build prompt** (plus template files) for creating new Docker-hosted apps with **Claude Code** or **OpenAI Codex**. DockerAppBlueprint itself is also a Docker app and must follow every rule below.

## 0. Before you write code
1. Inspect my reference app at https://github.com/jayvenco/productivity-suite.git (clone it to a temp folder). Copy its conventions for: repo layout, Dockerfile, docker-compose, Unraid template XML, README install section, update flow, and CI. Mirror them unless they contradict this prompt; tell me about any conflict.
2. Summarise your plan and the stack you chose (lightweight: e.g. Node/Express or Python/FastAPI + vanilla/Preact frontend, SQLite) in max 15 lines, then start building. Ask questions only if something blocks you.

## 1. What the app does
A wizard UI that asks, step by step, everything needed to produce a complete, high-quality build prompt for a **new** app. Output: 
- A copyable **prompt** (Markdown) with a Copy button and download.
- Tool-specific export, chosen per prompt: **Claude Code** (prompt + `CLAUDE.md`) or **OpenAI Codex** (prompt + `AGENTS.md`).
- Saved prompt history (edit, duplicate, delete, import/export as JSON).
- The app does **not** create repos or run code itself. The generated prompt instructs the coding agent to do that (see section 3).

### Wizard questions (one step at a time, with sensible defaults, "Recommended" marked)
1. App name, one-line purpose, target users.
2. **Style/weight**: lightweight / balanced / feature-rich.
3. **Visual design**: minimal / balanced / premium.
4. **Single-user or multi-user?** (multi-user adds roles, user management).
5. **Hermes Agent** must be able to connect? (yes → REST API + token auth + OpenAPI docs).
6. **Manageable via API calls?** Show the option (yes/no) with explanation of what it exposes.
7. **External APIs** needed? For each: which API and **what it is used for**.
8. **Database**: default SQLite. Only propose MySQL/PostgreSQL when justified, and explain why.
9. **Automated backups** to a `backup` folder? If yes: schedule, retention, and **import + export** in the UI.
10. **Staging and production?** Ask **per app**. If yes: code is pushed to `staging` first; after my approval it is promoted to production (see section 3).
11. **Container layout**: everything in ONE container by default; propose separate frontend/backend only when clearly better, and say why.
12. Extra features, free text. Then ask **follow-up questions** whenever an answer is unclear or incomplete.
13. **Review screen**: summary of all answers + the **improvement suggestions** (section 5) as toggles before the prompt is generated.

## 2. Rules baked into EVERY generated app prompt
- UI language: **English** always.
- Lightweight: small image (multi-stage build, alpine/slim base), low RAM/CPU, minimal dependencies.
- **Single container** unless separation is justified.
- **Auth**: password-protected login. Default account `admin` / `admin`, with a **forced password change on first login**. Hashed passwords (argon2/bcrypt), secure session cookies, rate-limited login.
- **Themes**: ship with **5 themes**, including at least one dark and one light; user can switch and it persists. Use CSS variables.
- **Fonts**: font selector with 5 common fonts (e.g. Inter, Roboto, Open Sans, Lato, system-ui) bundled locally, no external CDN.
- **Unraid**: default install path `/mnt/user/appdata/<appname>`; config, DB, backups and logs live under it via volumes. Include an **Unraid Community Applications template XML** (icon, WebUI port, paths, env vars, categories), so the app installs from the template and **updates through Docker (pull new image) in Unraid**.
- Healthcheck endpoint, graceful shutdown, non-root user where possible, timezone/PUID/PGID env vars.
- Publish image to GHCR (`ghcr.io/jayvenco/<appname>`) through GitHub Actions; tags `latest` and `staging` as applicable.
- Optional per answers: Hermes/API token management page, OpenAPI docs at `/api/docs`, backup/restore UI, external-API settings page.

## 3. Repo, docs and workflow rules in every generated prompt
- Every app gets its **own GitHub repo** under account **jayvenco** (use `gh repo create jayvenco/<appname>`). Never reuse another app's repo.
- Install/readme structure must match productivity-suite (docker run / compose / Unraid steps).
- The agent must **automatically update documentation** (README, CHANGELOG, API docs) with every change, and take **screenshots** where useful (headless browser such as Playwright) and store them in `docs/screenshots/`, referenced in the README.
- If staging was chosen: branches `develop` (staging) and `main` (production); images `:staging` and `:latest`; two Unraid templates with separate port and appdata folder; the agent pushes to staging, **stops and asks me to approve**, and only after approval promotes to production.
- Conventional commits, semantic version tags, GitHub Release notes.

## 4. DockerAppBlueprint's own features
- **Logo generator**: connected to the OpenAI API (images endpoint). Settings page stores the OpenAI key (encrypted at rest, or via env var `OPENAI_API_KEY`). In the wizard I can describe a logo, generate several variants, pick one, and download it (PNG + 256px icon for the Unraid template). Handle missing key/errors gracefully.
- **API for Hermes Agent**: REST API with Bearer tokens created in the UI (name, scope, revoke, last used). Endpoints to: list/create/update/delete saved prompts, run the wizard non-interactively from a JSON spec (returns the generated prompt), list improvement suggestions, trigger a logo generation, health/version. OpenAPI spec + docs page.
- Follows all rules in section 2 (5 themes, 5 fonts, login admin/admin with forced change, SQLite, backups with import/export, Unraid template, GHCR, staging/production question applied to itself: build it with `develop`+`main`).
- Settings: theme, font, OpenAI key, API tokens, backup config, default values for wizard answers (so my preferences prefill every new prompt).

## 5. Improvement suggestions the wizard always shows (toggleable, with one-line reason)
Offer these in the review step and add selected ones to the prompt:
- Health/readiness endpoints and Docker `HEALTHCHECK`
- Structured logging with log rotation and a log viewer
- `.env.example` and config validation at startup
- Security headers, CSRF protection, input validation, rate limiting
- Reverse-proxy readiness (base URL/path, forwarded headers, HTTPS notes for Unraid/NPM/Traefik)
- Optional 2FA/TOTP, session timeout, audit log
- Tests (unit + a smoke test in CI), linting, Dependabot/Renovate
- Multi-arch images (amd64 + arm64), image size budget
- Update notifications and an in-app "About / version / changelog" page
- Notifications (email, Discord, Telegram, ntfy, webhook)
- PWA/mobile-friendly layout, keyboard shortcuts, accessibility (WCAG AA)
- Data: soft delete, CSV/JSON import-export, seed/demo data
- Maintenance mode, resource limits in the Unraid template
- Agent-friendly repo: good `CLAUDE.md`/`AGENTS.md`, architecture doc, `docs/` folder, issue templates
- Prompt quality helpers: acceptance criteria, "definition of done" checklist, out-of-scope list

## 6. Deliverables
1. Working app in this folder with Dockerfile, `docker-compose.yml`, `.dockerignore`, `.env.example`.
2. Unraid template XML + icon, GitHub Actions workflow (GHCR), README (install via docker / compose / Unraid, update, backup, API usage), CHANGELOG, `CLAUDE.md`, screenshots in `docs/screenshots/`.
3. Initialise git, create `jayvenco/dockerappblueprint` with `gh`, push `develop` first, then **ask me for approval** before promoting to `main`.
4. Finish with a short report: what was built, how to install on Unraid, default login, what I should check.

Work in small verified steps (build the image, run it, test the login and wizard before moving on). Ask me only when blocked.
