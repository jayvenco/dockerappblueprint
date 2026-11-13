# Changelog

All notable changes to this project are documented here. Format: [Keep a Changelog](https://keepachangelog.com), versioning: [SemVer](https://semver.org).

## [0.1.0] - 2026-11-13
### Added
- Step-by-step wizard that generates a build prompt (plus `CLAUDE.md` / `AGENTS.md`) for new Docker apps, with follow-up questions and toggleable improvement suggestions.
- Saved prompt history with edit, duplicate, delete and JSON import/export.
- OpenAI logo generator with PNG and 256px icon download.
- REST API v1 with Bearer tokens (read/write scope) for Hermes Agent; OpenAPI spec and offline docs page.
- Login with forced password change from the default `admin`/`admin`, rate-limited sign-in, CSRF/Origin protection, security headers.
- 5 themes (2 light, 3 dark) and 5 bundled fonts.
- Automatic backups with retention, export and import/restore.
- Docker image (non-root via PUID/PGID), Unraid template, install script, GitHub Actions workflow (`main` -> `:latest`). The container listens on port 7773; the template and the install script ask which port to use on Unraid.
