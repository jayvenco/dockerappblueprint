# DockerAppBlueprint — API handbook for agents (Hermes Agent)

Base URL: `http://<unraid-ip>:7773/api/v1` · All requests and responses are JSON. Full route list with fields: `GET /api/openapi.json`.

## Authentication
Create a token in the app under **Settings → API tokens** (shown once). Send it on every request:

```
Authorization: Bearer <token>
Content-Type: application/json
```

Missing/invalid/revoked token → `401 {"detail": "..."}`. A **read** token may not create, change or delete anything (`403`). Test the connection: `GET /health` → `{"status":"ok","auth":"ok","scope":"write","version":"0.1.0"}`.

Token, key and backup management is deliberately **not** available through the API (browser session only).

## Conventions
- Lists: `GET /prompts` → `{"items": [...], "total": N, "limit": 100, "offset": 0}`; use `?limit=` (max 500) and `?offset=`. Newest first.
- Create: `POST` → `200` with the object (incl. `id`). Update: `PATCH` with only the fields that change. Delete: `DELETE` → `{"deleted": true, "id": N}`.
- Errors: unknown id `404`, invalid input `422` (`{"detail": {"errors": [...]}}`), logo problems `400` with a readable message.

## Typical flow for an agent
1. `GET /wizard/schema` — steps, defaults and improvement ids.
2. `POST /generate` with `{"spec": {...}}` — returns `prompt_md`, `context_md`, `context_name` and `open_questions`.
3. Answer `open_questions` by sending them back in `spec.followups` (`{"<question id>": "answer"}`) and generate again.
4. `POST /prompts` with the final spec to save it, then hand `prompt_md` to Claude Code/Codex.

## Spec fields (all optional except `app_name` and `purpose`)
| Key | Values |
|---|---|
| `app_name`, `purpose`, `target_users` | text |
| `tool` | `claude` (default) or `codex` |
| `weight` | `lightweight` (default), `balanced`, `feature-rich` |
| `design` | `minimal`, `balanced` (default), `premium` |
| `user_mode` | `single` (default) or `multi` |
| `hermes`, `api_managed` | booleans (`hermes: true` implies `api_managed`) |
| `external_apis` | `[{"name": "...", "purpose": "..."}]` |
| `database` | `sqlite` (default), `postgresql`, `mysql` (+ `database_reason`) |
| `backup`, `backup_schedule`, `backup_keep` | bool, `daily`/`weekly`, 1-90 |
| `containers` | `single` (default) or `split` (+ `containers_reason`) |
| `staging` | bool: `develop`/`main` flow with approval step |
| `github_owner` | default `jayvenco` |
| `improvements` | list of ids from `GET /suggestions` |
| `followups` | `{"<question id>": "answer"}` |
| `extra` | free text |

## Endpoints
| Action | Request |
|---|---|
| Health / auth check | `GET /health` |
| Version | `GET /version` |
| Wizard schema | `GET /wizard/schema` |
| Improvement suggestions | `GET /suggestions` |
| Follow-up questions | `POST /followups` `{"spec": {...}}` |
| Generate (optionally save) | `POST /generate` `{"spec": {...}, "save": false, "name": "..."}` (`save: true` needs a write token) |
| List / get | `GET /prompts`, `GET /prompts/{id}` |
| Create | `POST /prompts` `{"spec": {...}, "name": "optional"}` |
| Update | `PATCH /prompts/{id}` `{"name": "...", "spec": {...}}` (a new spec regenerates the prompt) |
| Delete | `DELETE /prompts/{id}` |
| Download Markdown | `GET /prompts/{id}/download?file=prompt\|context` |
| Export / import all | `GET /prompts/export`, `POST /prompts/import` |
| Generate logos | `POST /logos` `{"description": "...", "n": 3, "prompt_id": null}` (needs an OpenAI key in the app) |
| List logos | `GET /logos` |
| Logo files | `GET /logos/{id}/image.png`, `GET /logos/{id}/icon.png` (256x256) |
| Delete logo | `DELETE /logos/{id}` |

## Example
```bash
curl -s -X POST http://<unraid-ip>:7773/api/v1/generate \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"spec": {"app_name": "Recipe Vault", "purpose": "Store and search family recipes with photos and tags.", "staging": true}}'
```
