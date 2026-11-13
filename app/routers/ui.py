"""Cookie-only JSON endpoints behind the Settings page. Not available to API tokens on purpose."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import FONTS, THEMES, settings
from ..database import get_db
from ..deps import ui_user
from ..models import ApiToken, User
from ..security import new_api_token
from ..services import backup, store
from ..services.wizard import DEFAULTS

router = APIRouter(prefix="/ui", tags=["ui"], include_in_schema=False)


class Appearance(BaseModel):
    theme: str | None = None
    font: str | None = None


class KeyIn(BaseModel):
    key: str = ""


class TokenIn(BaseModel):
    name: str
    scope: str = "write"


class BackupCfg(BaseModel):
    enabled: bool
    schedule: str = "daily"
    keep: int = 7


@router.post("/appearance")
def appearance(body: Appearance, user: User = Depends(ui_user), db: Session = Depends(get_db)):
    if body.theme is not None:
        if body.theme not in THEMES:
            raise HTTPException(422, "Unknown theme")
        user.theme = body.theme
    if body.font is not None:
        if body.font not in FONTS:
            raise HTTPException(422, "Unknown font")
        user.font = body.font
    db.commit()
    return {"theme": user.theme, "font": user.font}


@router.post("/openai-key")
def openai_key(body: KeyIn, user: User = Depends(ui_user), db: Session = Depends(get_db)):
    key = body.key.strip()
    if key and not key.startswith("sk-"):
        raise HTTPException(422, "That does not look like an OpenAI key (should start with sk-).")
    store.set_openai_key(db, key)
    return {"configured": bool(store.openai_key(db)), "from_env": bool(settings.openai_api_key_env)}


@router.get("/tokens")
def list_tokens(user: User = Depends(ui_user), db: Session = Depends(get_db)):
    rows = db.query(ApiToken).order_by(ApiToken.id.desc()).all()
    return {"items": [{"id": t.id, "name": t.name, "prefix": t.prefix, "scope": t.scope, "revoked": t.revoked,
                       "created_at": t.created_at.strftime("%Y-%m-%d %H:%M"),
                       "last_used_at": t.last_used_at.strftime("%Y-%m-%d %H:%M") if t.last_used_at else None}
                      for t in rows]}


@router.post("/tokens")
def create_token(body: TokenIn, user: User = Depends(ui_user), db: Session = Depends(get_db)):
    if not body.name.strip():
        raise HTTPException(422, "Give the token a name (e.g. Hermes Agent).")
    if body.scope not in {"read", "write"}:
        raise HTTPException(422, "Scope must be read or write.")
    plain, prefix, digest = new_api_token()
    row = ApiToken(name=body.name.strip()[:80], prefix=prefix, token_hash=digest, scope=body.scope)
    db.add(row)
    db.commit()
    return {"id": row.id, "token": plain, "note": "Copy it now; it is never shown again."}


@router.delete("/tokens/{tid}")
def revoke_token(tid: int, user: User = Depends(ui_user), db: Session = Depends(get_db)):
    row = db.get(ApiToken, tid)
    if not row:
        raise HTTPException(404, "Token not found")
    row.revoked = True
    db.commit()
    return {"revoked": True}


@router.get("/backups")
def backups(user: User = Depends(ui_user), db: Session = Depends(get_db)):
    return {"config": store.backup_config(db), "items": backup.list_backups()}


@router.post("/backups/config")
def backup_config(body: BackupCfg, user: User = Depends(ui_user), db: Session = Depends(get_db)):
    if body.schedule not in {"daily", "weekly"}:
        raise HTTPException(422, "Schedule must be daily or weekly")
    store.put(db, "backup_enabled", "1" if body.enabled else "0")
    store.put(db, "backup_schedule", body.schedule)
    store.put(db, "backup_keep", str(max(1, min(90, body.keep))))
    return {"config": store.backup_config(db)}


@router.post("/backups")
async def backup_now(user: User = Depends(ui_user), db: Session = Depends(get_db)):
    path = await asyncio.to_thread(backup.create_backup, "manual")
    backup.prune(store.backup_config(db)["keep"])
    return {"name": path.name}


@router.get("/backups/{name}")
def backup_download(name: str, user: User = Depends(ui_user)):
    try:
        path = backup.safe_path(name)
    except backup.BackupError as exc:
        raise HTTPException(404, str(exc)) from exc
    return FileResponse(path, media_type="application/zip", filename=path.name)


@router.delete("/backups/{name}")
def backup_delete(name: str, user: User = Depends(ui_user)):
    try:
        backup.safe_path(name).unlink()
    except backup.BackupError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"deleted": True}


@router.post("/backups/restore")
async def backup_restore(response: Response, file: UploadFile = File(...), user: User = Depends(ui_user)):
    data = await file.read()
    if len(data) > 200 * 1024 * 1024:
        raise HTTPException(413, "Backup is too large (max 200 MB).")
    try:
        await asyncio.to_thread(backup.restore, data)
    except backup.BackupError as exc:
        raise HTTPException(400, str(exc)) from exc
    response.delete_cookie(settings.session_cookie_name)
    return {"restored": True, "note": "Restored. Sign in again."}


@router.post("/wizard-defaults")
def wizard_defaults(body: dict[str, Any], user: User = Depends(ui_user), db: Session = Depends(get_db)):
    allowed = {"tool", "weight", "design", "user_mode", "hermes", "api_managed", "database", "backup",
               "backup_schedule", "backup_keep", "staging", "containers", "github_owner"}
    clean = {k: v for k, v in body.items() if k in allowed and k in DEFAULTS}
    store.put_json(db, "wizard_defaults", clean)
    return {"saved": clean}
