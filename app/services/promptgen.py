"""Turns wizard answers into a build prompt (Markdown) plus CLAUDE.md / AGENTS.md content."""
from __future__ import annotations

from typing import Any

from .wizard import IMPROVEMENTS, followups, merge_spec, slugify

IMPROVEMENT_TEXT = {
    "health": "Provide `/health` (liveness) and `/ready` (DB reachable) endpoints and a Docker `HEALTHCHECK` that uses them.",
    "logging": "Use structured logging to stdout and a rotating file in `/app/data/logs`; add a log viewer page for admins.",
    "env_validation": "Ship `.env.example` and validate configuration at startup with a clear error message.",
    "security": "Add security headers, CSRF/Origin protection, server-side input validation and rate limiting on login and API.",
    "proxy": "Make the app reverse-proxy ready: honour `X-Forwarded-*` headers, support a base URL, document HTTPS setups for Nginx Proxy Manager/Traefik.",
    "twofa": "Add optional TOTP 2FA, configurable session timeout and an audit log of sign-ins and settings changes.",
    "tests": "Add unit tests plus a CI smoke test (container starts, health is green, login works), a linter and Dependabot.",
    "multiarch": "Build multi-arch images (linux/amd64 + linux/arm64) and keep the image under a stated size budget.",
    "about": "Add an About page with version, changelog and a non-intrusive 'update available' notice.",
    "notifications": "Add notifications (email, Discord, Telegram, ntfy, webhook) configurable in Settings.",
    "pwa": "Make the UI responsive and installable as a PWA, add keyboard shortcuts and meet WCAG AA contrast/focus rules.",
    "data_tools": "Use soft delete with undo, CSV/JSON import-export of user data and optional seed/demo data.",
    "maintenance": "Add a maintenance mode toggle and recommended CPU/memory limits in the Unraid template.",
    "agent_repo": "Keep the repo agent-friendly: `docs/architecture.md`, a `docs/` folder, issue templates, and an up-to-date context file.",
    "prompt_quality": "Work from the acceptance criteria and definition of done below; respect the out-of-scope list.",
}

WEIGHT_TEXT = {
    "lightweight": "Lightweight: fewest dependencies, smallest possible image, low idle RAM/CPU, no heavy frameworks or build chains unless unavoidable.",
    "balanced": "Balanced: a sensible feature set with a modest dependency list; keep the image small.",
    "feature-rich": "Feature-rich: a broad feature set is welcome, but keep idle resource use reasonable and the image as small as the features allow.",
}
DESIGN_TEXT = {
    "minimal": "Minimal: clean, fast, utilitarian UI with little decoration.",
    "balanced": "Balanced: friendly, clean UI with consistent spacing, clear hierarchy and tasteful accents.",
    "premium": "Premium: polished UI, refined typography and spacing, subtle motion and depth, attention to empty/loading/error states.",
}


def port_for(slug: str) -> int:
    return 8800 + sum(ord(c) for c in slug) % 100


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {i}" for i in items)


def context_file_name(tool: str) -> str:
    return "AGENTS.md" if tool == "codex" else "CLAUDE.md"


def build_context_md(s: dict[str, Any]) -> str:
    slug = slugify(s["app_name"])
    port = port_for(slug)
    tool_line = "OpenAI Codex" if s["tool"] == "codex" else "Claude Code"
    return f"""# {s['app_name']} — {context_file_name(s['tool'])}

Context for {tool_line}. Keep this file current whenever the project changes.

## What this is
{s['purpose'].strip()}

Users: {s['target_users'].strip() or 'not specified'}.

## Rules
- UI and all documentation are in **English**.
- Lightweight first: {WEIGHT_TEXT[s['weight']].split(': ', 1)[1]}
- Database: **{s['database']}**, data lives in `/app/data` (host: `/mnt/user/appdata/{slug}/data`).
- Auth: password-protected login, default `admin`/`admin`, **forced password change on first login**.
- 5 themes (at least one light and one dark) and a font selector with 5 bundled fonts; no external CDNs.
- Container port 8000, suggested host port {port}. Image: `ghcr.io/{s['github_owner']}/{slug}`.
- Update docs (README, CHANGELOG, API docs) with every change; refresh screenshots in `docs/screenshots/`.
- Conventional commits, semantic version tags.
{'- Staging flow: `develop` -> `:staging` image; after the owner approves, promote to `main` -> `:latest`.' if s['staging'] else '- Single release flow: `main` -> `:latest`.'}

## Commands
- Run locally: `docker compose up --build` (http://localhost:8000)
- Tests: see README -> Tests
"""


def build_prompt(spec: dict[str, Any]) -> dict[str, Any]:
    s = merge_spec(spec)
    slug = slugify(s["app_name"])
    port = port_for(slug)
    owner = s["github_owner"] or "jayvenco"
    fu = s["followups"]
    ctx_name = context_file_name(s["tool"])
    tool_name = "OpenAI Codex" if s["tool"] == "codex" else "Claude Code"
    imp = [i for i in IMPROVEMENTS if i["id"] in s["improvements"]]
    api_on = s["hermes"] or s["api_managed"]
    L: list[str] = []
    w = L.append

    w(f"# Build prompt: {s['app_name']}\n")
    w(f"Paste this into **{tool_name}**, started in an empty folder named `{slug}`.\n\n---\n")
    w(f"You are building **{s['app_name']}**, a self-hosted app that runs as a Docker container on an Unraid NAS. "
      "Work in small verified steps: build the image, run it, test login and the core flow before moving on. "
      "Ask me only when you are truly blocked.\n")

    w("## 0. Before you write code")
    w(_bullets([
        "Clone my reference app https://github.com/jayvenco/productivity-suite.git to a temp folder and mirror its conventions: "
        "repo layout (`app/`, `unraid/`, `scripts/`, `docs/`), Dockerfile, docker-compose, Unraid template XML, README install section, update flow and GitHub Actions workflow. "
        "Tell me about any conflict with this prompt.",
        "Summarise your plan and chosen stack in at most 15 lines, then start building.",
    ]) + "\n")

    w("## 1. The app")
    w(f"**Purpose:** {s['purpose'].strip()}\n")
    w(f"**Users:** {s['target_users'].strip() or 'not specified'}\n")
    if fu.get("purpose_detail"):
        w(f"**Main workflow:** {fu['purpose_detail']}\n")
    if fu.get("target_users"):
        w(f"**User profile:** {fu['target_users']}\n")
    if s["extra"].strip():
        w(f"**Extra features requested:**\n\n{s['extra'].strip()}\n")
    if fu.get("top_features"):
        w(f"**Top 3 features:** {fu['top_features']}\n")

    w("## 2. Product decisions")
    decisions = [
        f"Weight: {WEIGHT_TEXT[s['weight']]}",
        f"Visual design: {DESIGN_TEXT[s['design']]}",
        f"Access: **{'multi-user' if s['user_mode'] == 'multi' else 'single-user'}**"
        + (" with roles and a user-management page." if s["user_mode"] == "multi" else "."),
    ]
    if fu.get("roles"):
        decisions.append(f"Roles: {fu['roles']}")
    if fu.get("design_refs"):
        decisions.append(f"Design reference: {fu['design_refs']}")
    w(_bullets(decisions) + "\n")

    w("## 3. Architecture")
    arch = []
    if s["containers"] == "split":
        arch.append("**Two containers** (frontend and backend are separated) with a compose file that wires them together. "
                    f"Reason: {s['containers_reason'] or fu.get('containers_reason', 'see owner')}")
    else:
        arch.append("**Everything runs in ONE container** (frontend, backend, scheduler and database file together).")
    if s["database"] == "sqlite":
        arch.append("Database: **SQLite** in `/app/data` (WAL mode). No extra database container.")
    else:
        arch.append(f"Database: **{s['database']}** because: {s['database_reason'] or fu.get('database_reason', 'see owner')}. "
                    "Provide it as a separate container in compose and document the Unraid setup; keep SQLite as a documented fallback if feasible.")
    arch.append("Prefer a small, boring stack (Python 3.12 + FastAPI + SQLAlchemy + Jinja2 + vanilla JS, as in productivity-suite) unless the app clearly needs something else.")
    w(_bullets(arch) + "\n")

    w("## 4. Rules for every app")
    rules = [
        "UI language and all documentation: **English**.",
        "Lightweight: multi-stage build, slim/alpine base, minimal dependencies, low RAM/CPU.",
        "**Login**: password-protected. Default account `admin` / `admin` with a **forced password change on first login**. "
        "Hash passwords (bcrypt/argon2), secure session cookies, rate-limited login.",
        "**5 themes** (at least one dark and one light) using CSS variables; the choice persists per user.",
        "**Font selector** with 5 common fonts (Inter, Roboto, Open Sans, Lato, system-ui) bundled locally; no external CDN.",
        "Healthcheck endpoint, graceful shutdown, non-root user where possible, `TZ`, `PUID` and `PGID` environment variables.",
        "Config, database, logs and backups live under one data volume `/app/data`.",
    ]
    w(_bullets(rules) + "\n")

    w("## 5. Unraid installation and updates")
    w(_bullets([
        f"Default appdata path: `/mnt/user/appdata/{slug}/data` mapped to `/app/data`.",
        f"Container port 8000, default host port {port}.",
        f"Provide `unraid/{slug}.xml` (Community Applications template: icon, WebUI `http://[IP]:[PORT:8000]/`, paths, variables, category), `unraid/icon.png`, "
        "`docker-compose.yml`, and `scripts/install-unraid.sh` modelled on productivity-suite so a user can install with one command or from the template.",
        "Updates happen from Unraid by pulling the new image (Docker tab -> force update); data must survive updates. Add the `net.unraid.docker.*` labels like the reference script.",
        f"Publish images to **GHCR** `ghcr.io/{owner}/{slug}` with GitHub Actions (`provenance: false`, `sbom: false`, as in the reference workflow). Add the `org.opencontainers.image.source` label.",
    ]) + "\n")

    w("## 6. Repository, documentation and workflow")
    flow = [
        f"Create a **new repo** with `gh repo create {owner}/{slug}` — never reuse another app's repo.",
        "README layout like productivity-suite: logo, screenshots, features, install via docker run / compose / Unraid, update, backup, API usage, tests.",
        "Keep **README, CHANGELOG and API docs updated automatically** with every change.",
        "Take **screenshots** where useful with a headless browser (Playwright) into `docs/screenshots/` and reference them in the README (use demo data only).",
        "Conventional commits, semantic version tags and GitHub Release notes.",
    ]
    if s["staging"]:
        flow += [
            "**Staging and production**: branches `develop` (staging) and `main` (production). The workflow publishes `:staging` from `develop` and `:latest` from `main`.",
            f"Provide two Unraid templates (`unraid/{slug}.xml` and `unraid/{slug}-staging.xml`) with separate ports ({port} and {port + 100}) and appdata folders (`{slug}` and `{slug}-staging`).",
            "Push to `develop` first, then **stop and ask me to approve**"
            + (f" ({fu['staging_approval']})" if fu.get("staging_approval") else "")
            + ". Only after my approval promote to `main`.",
        ]
    else:
        flow.append("Single release flow: push to `main`, the workflow publishes `:latest`.")
    w(_bullets(flow) + "\n")

    if s["backup"]:
        w("## 7. Backups")
        w(_bullets([
            f"Automated **{s['backup_schedule']}** backups into `/app/data/backup`, keeping the last **{s['backup_keep']}** (configurable in Settings).",
            "Use the SQLite online backup API so backups are consistent while the app runs.",
            "UI for: create backup now, list, download, **export**, **import/restore** (take a safety copy before restoring).",
        ]) + "\n")
    else:
        w("## 7. Backups\n- No automated backups requested. Document how to back up `/app/data` manually.\n")

    w("## 8. Integrations and API")
    integ: list[str] = []
    if s["external_apis"]:
        for a in s["external_apis"]:
            extra = fu.get(f"api_{slugify(a['name'])}", "")
            integ.append(f"External API **{a['name']}**: {a['purpose'] or 'purpose not given'}"
                         + (f" — {extra}" if extra else "")
                         + ". Put its key/URL in Settings (and env var), handle errors and timeouts gracefully, never hard-code secrets.")
    else:
        integ.append("No external APIs are required.")
    if s["hermes"]:
        integ.append("**Hermes Agent must be able to connect**: REST API under `/api/v1` with Bearer tokens created in the UI (name, read/write scope, revoke, last used), "
                     "an OpenAPI spec at `/api/openapi.json` and an API docs page at `/api/docs` that works offline.")
        if fu.get("hermes_scope"):
            integ.append(f"Hermes scope: {fu['hermes_scope']}")
    if api_on and not s["hermes"]:
        integ.append("The app must be **manageable via API calls**: REST API under `/api/v1`, Bearer tokens created in the UI, OpenAPI spec and docs page.")
        if fu.get("api_scope"):
            integ.append(f"API scope: {fu['api_scope']}")
    if api_on:
        integ.append("Add an `AGENT_API.md` handbook (base URL, auth, conventions, endpoint table) like productivity-suite.")
    else:
        integ.append("No public API is required; do not expose one.")
    w(_bullets(integ) + "\n")

    if imp:
        w("## 9. Improvements to include")
        w(_bullets([IMPROVEMENT_TEXT[i["id"]] for i in imp]) + "\n")

    if "prompt_quality" in s["improvements"]:
        w("## 10. Acceptance criteria and definition of done")
        w(_bullets([
            "`docker compose up --build` starts the app; the health endpoint is green.",
            "Login works with `admin`/`admin` and forces a password change; wrong passwords are rate-limited.",
            "All 5 themes and all 5 fonts work and persist after reload.",
            "Data survives a container re-create (volume) and an image update.",
            "README, CHANGELOG and screenshots match the shipped behaviour.",
            "The GitHub Actions workflow builds and publishes the image.",
        ]))
        w("\n**Out of scope:** anything not listed above; ask before adding it.\n")

    w("## 11. Deliverables")
    w(_bullets([
        "Working app with `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.env.example`.",
        f"`unraid/{slug}.xml` + `unraid/icon.png`, `scripts/install-unraid.sh`, `.github/workflows/docker-publish.yml`.",
        f"README, CHANGELOG, `{ctx_name}`" + (", `AGENT_API.md`" if api_on else "") + ", screenshots in `docs/screenshots/`.",
        f"Git initialised, repo `{owner}/{slug}` created with `gh`, first push done"
        + (" to `develop`, then ask for my approval before `main`." if s["staging"] else " to `main`."),
        "Finish with a short report: what was built, how to install on Unraid, the default login, and what I should check.",
    ]) + "\n")
    if s["logo"]:
        w(f"A logo file is provided as `{s['logo']}`: use it as `docs/logo.png` and `unraid/icon.png` (256x256).\n")

    prompt_md = "\n".join(L).rstrip() + "\n"
    return {
        "slug": slug,
        "prompt_md": prompt_md,
        "context_md": build_context_md(s),
        "context_name": ctx_name,
        "open_questions": followups(s),
        "spec": s,
    }
