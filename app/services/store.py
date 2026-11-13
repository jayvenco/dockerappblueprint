"""Tiny key/value settings store on top of the settings table."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from ..config import settings
from ..models import Setting
from ..security import decrypt, encrypt


def get(db: Session, key: str, default: str = "") -> str:
    row = db.get(Setting, key)
    return row.value if row else default


def put(db: Session, key: str, value: str) -> None:
    row = db.get(Setting, key)
    if row:
        row.value = value
    else:
        db.add(Setting(key=key, value=value))
    db.commit()


def get_json(db: Session, key: str, default: Any) -> Any:
    raw = get(db, key, "")
    try:
        return json.loads(raw) if raw else default
    except json.JSONDecodeError:
        return default


def put_json(db: Session, key: str, value: Any) -> None:
    put(db, key, json.dumps(value))


def openai_key(db: Session) -> str:
    """Env var wins over the key entered in Settings."""
    if settings.openai_api_key_env:
        return settings.openai_api_key_env
    stored = get(db, "openai_key")
    return decrypt(stored) if stored else ""


def set_openai_key(db: Session, key: str) -> None:
    put(db, "openai_key", encrypt(key) if key else "")


def backup_config(db: Session) -> dict[str, Any]:
    return {
        "enabled": get(db, "backup_enabled", "1" if settings.backup_enabled_default else "0") == "1",
        "schedule": get(db, "backup_schedule", "daily"),
        "keep": int(get(db, "backup_keep", str(settings.backup_keep_default)) or 7),
    }


def wizard_defaults(db: Session) -> dict[str, Any]:
    return get_json(db, "wizard_defaults", {})
