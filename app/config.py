from __future__ import annotations

import os
import secrets
from pathlib import Path

from . import __version__

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR = DATA_DIR / "backup"
LOGO_DIR = DATA_DIR / "logos"
for _d in (BACKUP_DIR, LOGO_DIR):
    _d.mkdir(parents=True, exist_ok=True)

SECRET_KEY_FILE = DATA_DIR / ".secret_key"


def _load_or_create_secret_key() -> str:
    """Random secret generated on first start and kept in the data volume, so no .env is needed
    and sessions survive container updates."""
    if SECRET_KEY_FILE.exists():
        return SECRET_KEY_FILE.read_text().strip()
    key = secrets.token_hex(32)
    SECRET_KEY_FILE.write_text(key)
    SECRET_KEY_FILE.chmod(0o600)
    return key


def _env(name: str, default: str = "") -> str:
    value = os.environ.get(name, "")
    return value if value != "" else default


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name, "")
    if value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    app_name = "DockerAppBlueprint"
    version = __version__
    database_url = f"sqlite:///{DATA_DIR / 'app.db'}"
    secret_key = _load_or_create_secret_key()
    session_cookie_name = "dab_session"
    session_max_age_seconds = 60 * 60 * 24 * 14
    default_username = "admin"
    default_password = "admin"
    default_theme = _env("DEFAULT_THEME", "midnight")
    cookie_secure = _env_bool("COOKIE_SECURE", False)
    openai_api_key_env = _env("OPENAI_API_KEY")
    openai_base_url = _env("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    openai_image_model = _env("OPENAI_IMAGE_MODEL", "gpt-image-1")
    backup_enabled_default = _env_bool("BACKUP_ENABLED", True)
    backup_keep_default = int(_env("BACKUP_KEEP", "7"))
    github_owner = "jayvenco"


settings = Settings()

THEMES = {
    "daylight": "Daylight (light)",
    "midnight": "Midnight (dark)",
    "nord": "Nord (dark)",
    "sand": "Sand (light)",
    "forest": "Forest (dark)",
}

FONTS = {
    "inter": ("Inter", "'Inter', system-ui, sans-serif"),
    "roboto": ("Roboto", "'Roboto', system-ui, sans-serif"),
    "open-sans": ("Open Sans", "'Open Sans', system-ui, sans-serif"),
    "lato": ("Lato", "'Lato', system-ui, sans-serif"),
    "system": ("System UI", "system-ui, -apple-system, 'Segoe UI', sans-serif"),
}
