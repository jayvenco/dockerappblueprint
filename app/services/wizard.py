"""Wizard definition: steps, defaults, improvement suggestions and follow-up questions.

The wizard UI renders this schema (served at /api/v1/wizard/schema), so adding a question here
adds it to the UI, the API and the generated prompt validation at once.
"""
from __future__ import annotations

import re
from typing import Any

IMPROVEMENTS: list[dict[str, Any]] = [
    {"id": "health", "label": "Health/readiness endpoints + Docker HEALTHCHECK", "reason": "Unraid and monitoring can see when the app is really up.", "default": True},
    {"id": "logging", "label": "Structured logging with rotation and a log viewer", "reason": "Debugging on a NAS without SSH.", "default": True},
    {"id": "env_validation", "label": ".env.example and config validation at startup", "reason": "Fails fast with a clear message instead of half-working.", "default": True},
    {"id": "security", "label": "Security headers, CSRF protection, input validation, rate limiting", "reason": "Cheap hardening for anything exposed on a LAN or reverse proxy.", "default": True},
    {"id": "proxy", "label": "Reverse-proxy readiness (base URL, forwarded headers, HTTPS notes)", "reason": "Works behind Nginx Proxy Manager, Traefik or Cloudflare Tunnel.", "default": True},
    {"id": "twofa", "label": "Optional 2FA/TOTP, session timeout, audit log", "reason": "Extra protection when the app is reachable from outside.", "default": False},
    {"id": "tests", "label": "Tests (unit + CI smoke test), linting, Dependabot", "reason": "Updates through Unraid stay safe.", "default": True},
    {"id": "multiarch", "label": "Multi-arch images (amd64 + arm64) and an image size budget", "reason": "Runs on Raspberry Pi and keeps pulls fast.", "default": False},
    {"id": "about", "label": "About page with version, changelog and update notification", "reason": "You can see which version runs and when to update.", "default": True},
    {"id": "notifications", "label": "Notifications (email, Discord, Telegram, ntfy, webhook)", "reason": "Backups and failures reach you.", "default": False},
    {"id": "pwa", "label": "PWA/mobile-friendly layout, keyboard shortcuts, WCAG AA accessibility", "reason": "Usable on a phone and by everyone.", "default": True},
    {"id": "data_tools", "label": "Soft delete, CSV/JSON import-export, seed/demo data", "reason": "Safer deletes and an easy first impression.", "default": False},
    {"id": "maintenance", "label": "Maintenance mode and resource limits in the Unraid template", "reason": "Predictable behaviour on a shared NAS.", "default": False},
    {"id": "agent_repo", "label": "Agent-friendly repo: architecture doc, docs/ folder, issue templates", "reason": "Future changes by Claude Code or Codex start faster and cleaner.", "default": True},
    {"id": "prompt_quality", "label": "Acceptance criteria, definition-of-done checklist, out-of-scope list", "reason": "Fewer misunderstandings and less rework.", "default": True},
]

DEFAULTS: dict[str, Any] = {
    "app_name": "",
    "purpose": "",
    "target_users": "",
    "tool": "claude",
    "weight": "lightweight",
    "design": "balanced",
    "user_mode": "single",
    "hermes": False,
    "api_managed": False,
    "external_apis": [],
    "database": "sqlite",
    "database_reason": "",
    "backup": True,
    "backup_schedule": "daily",
    "backup_keep": 7,
    "staging": False,
    "containers": "single",
    "containers_reason": "",
    "extra": "",
    "github_owner": "jayvenco",
    "improvements": [i["id"] for i in IMPROVEMENTS if i["default"]],
    "followups": {},
    "logo": "",
}


def _opt(value: str, label: str, desc: str = "", recommended: bool = False) -> dict[str, Any]:
    return {"value": value, "label": label, "desc": desc, "recommended": recommended}


STEPS: list[dict[str, Any]] = [
    {
        "id": "basics", "title": "The basics",
        "help": "Name, purpose and audience. The purpose sentence is the most important input in the whole prompt.",
        "fields": [
            {"key": "app_name", "type": "text", "label": "App name", "placeholder": "e.g. Recipe Vault", "required": True},
            {"key": "purpose", "type": "textarea", "label": "What does it do? (2-3 sentences)", "placeholder": "Describe the problem it solves and the main workflow.", "required": True},
            {"key": "target_users", "type": "text", "label": "Who will use it?", "placeholder": "e.g. just me, my family, a small team"},
        ],
    },
    {
        "id": "tool", "title": "Target AI tool",
        "help": "The build prompt is tuned for the tool that will write the code.",
        "fields": [{"key": "tool", "type": "choice", "label": "Build with", "options": [
            _opt("claude", "Claude Code", "Prompt + CLAUDE.md", True),
            _opt("codex", "OpenAI Codex", "Prompt + AGENTS.md"),
        ]}],
    },
    {
        "id": "weight", "title": "Weight and look",
        "help": "Controls how many dependencies, features and how much polish the app gets.",
        "fields": [
            {"key": "weight", "type": "choice", "label": "Style / weight", "options": [
                _opt("lightweight", "Lightweight", "Minimal dependencies, smallest image, few features.", True),
                _opt("balanced", "Balanced", "Sensible feature set, still small."),
                _opt("feature-rich", "Feature-rich", "Many features; a larger image is acceptable."),
            ]},
            {"key": "design", "type": "choice", "label": "Visual design", "options": [
                _opt("minimal", "Minimal", "Plain, fast, utilitarian."),
                _opt("balanced", "Balanced", "Clean and friendly.", True),
                _opt("premium", "Premium", "Polished: motion, depth, refined typography."),
            ]},
        ],
    },
    {
        "id": "users", "title": "Users and access",
        "help": "Every app has a password-protected login with admin/admin that must be changed on first login.",
        "fields": [
            {"key": "user_mode", "type": "choice", "label": "Single-user or multi-user?", "options": [
                _opt("single", "Single-user", "One account, simplest and lightest.", True),
                _opt("multi", "Multi-user", "Roles and user management included."),
            ]},
            {"key": "hermes", "type": "toggle", "label": "Must Hermes Agent be able to connect?", "desc": "Adds REST API + Bearer tokens + OpenAPI docs."},
            {"key": "api_managed", "type": "toggle", "label": "Make the app manageable through API calls?", "desc": "Exposes create/read/update/delete of the app's own data and settings over the API (token protected). Implied when Hermes is on."},
        ],
    },
    {
        "id": "external", "title": "External APIs",
        "help": "Does a feature depend on a third-party API? Add one line per API and say what it is for.",
        "fields": [{"key": "external_apis", "type": "list", "label": "External APIs", "item_fields": [
            {"key": "name", "label": "API / service", "placeholder": "e.g. OpenWeatherMap"},
            {"key": "purpose", "label": "What is it used for?", "placeholder": "e.g. show a 5-day forecast on the dashboard"},
        ]}],
    },
    {
        "id": "data", "title": "Database and backups",
        "help": "SQLite is the default. Another engine is only proposed when it is really needed.",
        "fields": [
            {"key": "database", "type": "choice", "label": "Database", "options": [
                _opt("sqlite", "SQLite", "File in the data volume, zero extra containers.", True),
                _opt("postgresql", "PostgreSQL", "Only for heavy concurrent writes or huge data."),
                _opt("mysql", "MySQL / MariaDB", "Only if you already run one you want to reuse."),
            ]},
            {"key": "database_reason", "type": "text", "label": "Why not SQLite?", "show_if": {"key": "database", "not": "sqlite"}},
            {"key": "backup", "type": "toggle", "label": "Automated backups to a backup folder?", "desc": "Includes import and export in the UI."},
            {"key": "backup_schedule", "type": "choice", "label": "Backup schedule", "show_if": {"key": "backup", "eq": True}, "options": [
                _opt("daily", "Daily", "", True), _opt("weekly", "Weekly")]},
            {"key": "backup_keep", "type": "number", "label": "Backups to keep", "show_if": {"key": "backup", "eq": True}, "min": 1, "max": 90},
        ],
    },
    {
        "id": "deploy", "title": "Containers and release flow",
        "help": "One container is the default. Staging adds a second, separately approved release path.",
        "fields": [
            {"key": "containers", "type": "choice", "label": "Container layout", "options": [
                _opt("single", "One container", "Frontend, backend and database file together.", True),
                _opt("split", "Separate frontend and backend", "Only when clearly better."),
            ]},
            {"key": "containers_reason", "type": "text", "label": "Why separate?", "show_if": {"key": "containers", "eq": "split"}},
            {"key": "staging", "type": "toggle", "label": "Staging and production?", "desc": "Code is pushed to staging first; after your approval it is promoted to production."},
            {"key": "github_owner", "type": "text", "label": "GitHub account for the repo"},
        ],
    },
    {
        "id": "extra", "title": "Extra features",
        "help": "Anything else the app should do. Free text. The next step may ask follow-up questions.",
        "fields": [{"key": "extra", "type": "textarea", "label": "Extra features / wishes", "placeholder": "Optional"}],
    },
]


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return slug or "my-app"


def merge_spec(spec: dict[str, Any] | None) -> dict[str, Any]:
    out = {**DEFAULTS, "improvements": list(DEFAULTS["improvements"]), "followups": {}}
    for key, value in (spec or {}).items():
        if key in DEFAULTS:
            out[key] = value
    fu = out["followups"] if isinstance(out["followups"], dict) else {}
    out["followups"] = {str(k): str(v).strip() for k, v in fu.items() if str(v).strip()}
    if out["hermes"]:
        out["api_managed"] = True
    out["external_apis"] = [
        {"name": str(a.get("name", "")).strip(), "purpose": str(a.get("purpose", "")).strip()}
        for a in (out["external_apis"] or []) if isinstance(a, dict) and str(a.get("name", "")).strip()
    ]
    known = {i["id"] for i in IMPROVEMENTS}
    out["improvements"] = [i for i in out["improvements"] if i in known]
    try:
        out["backup_keep"] = max(1, min(90, int(out["backup_keep"])))
    except (TypeError, ValueError):
        out["backup_keep"] = 7
    return out


def validate_spec(spec: dict[str, Any]) -> list[str]:
    errors = []
    if not spec.get("app_name", "").strip():
        errors.append("app_name is required")
    if not spec.get("purpose", "").strip():
        errors.append("purpose is required")
    if spec.get("tool") not in {"claude", "codex"}:
        errors.append("tool must be 'claude' or 'codex'")
    if spec.get("weight") not in {"lightweight", "balanced", "feature-rich"}:
        errors.append("weight must be lightweight, balanced or feature-rich")
    if spec.get("design") not in {"minimal", "balanced", "premium"}:
        errors.append("design must be minimal, balanced or premium")
    if spec.get("user_mode") not in {"single", "multi"}:
        errors.append("user_mode must be single or multi")
    if spec.get("database") not in {"sqlite", "postgresql", "mysql"}:
        errors.append("database must be sqlite, postgresql or mysql")
    if spec.get("containers") not in {"single", "split"}:
        errors.append("containers must be single or split")
    return errors


def followups(spec: dict[str, Any]) -> list[dict[str, str]]:
    """Questions to ask when an answer is unclear or incomplete."""
    s = merge_spec(spec)
    qs: list[dict[str, str]] = []

    def add(qid: str, question: str) -> None:
        if qid not in s["followups"]:
            qs.append({"id": qid, "question": question})

    if len(s["purpose"].strip()) < 40:
        add("purpose_detail", "Your purpose is short. What is the main workflow, step by step, from opening the app to the result?")
    if not s["target_users"].strip():
        add("target_users", "Who are the users and how technical are they?")
    for api in s["external_apis"]:
        if len(api["purpose"]) < 8:
            add(f"api_{slugify(api['name'])}", f"What exactly is {api['name']} used for, and which data is sent to or received from it?")
    if s["database"] != "sqlite" and len(s["database_reason"].strip()) < 8:
        add("database_reason", "SQLite is the default. Why do you need " + s["database"] + " (concurrency, data size, existing server)?")
    if s["containers"] == "split" and len(s["containers_reason"].strip()) < 8:
        add("containers_reason", "One container is the default. Why must frontend and backend be separate?")
    if s["user_mode"] == "multi":
        add("roles", "Which roles are needed (e.g. admin, editor, viewer) and what may each role do?")
    if s["hermes"]:
        add("hermes_scope", "Which actions should Hermes Agent perform: read-only, create/update data, or full management?")
    elif s["api_managed"]:
        add("api_scope", "Which parts of the app must be controllable through the API?")
    if s["weight"] == "feature-rich" and len(s["extra"].strip()) < 10:
        add("top_features", "Feature-rich was chosen. Which 3 features matter most?")
    if s["staging"]:
        add("staging_approval", "How do you want to approve a staging release (a chat reply, a GitHub PR, a tag)?")
    if s["design"] == "premium":
        add("design_refs", "Premium design: name an app or website whose look you like, or describe the mood.")
    return qs
