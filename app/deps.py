from __future__ import annotations

import datetime as dt

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import ApiToken, User
from .security import hash_token, read_session


class NeedLogin(Exception):
    pass


class NeedPasswordChange(Exception):
    pass


def session_user(request: Request, db: Session) -> User | None:
    uid = read_session(request.cookies.get(settings.session_cookie_name))
    return db.get(User, uid) if uid else None


def page_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = session_user(request, db)
    if not user:
        raise NeedLogin()
    if user.must_change_password:
        raise NeedPasswordChange()
    return user


def ui_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Cookie-only JSON endpoints used by the web UI (settings, tokens, backups)."""
    user = session_user(request, db)
    if not user:
        raise HTTPException(401, "Not signed in")
    if user.must_change_password:
        raise HTTPException(403, "Change the default password first")
    return user


class Actor:
    def __init__(self, scope: str, user: User | None = None, token: ApiToken | None = None):
        self.scope, self.user, self.token = scope, user, token

    def require_write(self) -> None:
        if self.scope != "write":
            raise HTTPException(403, "This token is read-only")


def api_actor(request: Request, db: Session = Depends(get_db)) -> Actor:
    """Bearer token (scoped) or a signed-in browser session (full access)."""
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        row = db.query(ApiToken).filter(ApiToken.token_hash == hash_token(header[7:].strip())).first()
        if not row or row.revoked:
            raise HTTPException(401, "Invalid or revoked API token")
        row.last_used_at = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None, microsecond=0)
        db.commit()
        return Actor(row.scope, token=row)
    user = session_user(request, db)
    if user and not user.must_change_password:
        return Actor("write", user=user)
    raise HTTPException(401, "Missing or invalid credentials (use 'Authorization: Bearer <token>')")


def write_actor(actor: Actor = Depends(api_actor)) -> Actor:
    actor.require_write()
    return actor
