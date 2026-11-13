from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..config import FONTS, THEMES, settings
from ..database import get_db
from ..deps import page_user, session_user
from ..models import PromptRecord, User
from ..security import hash_password, login_limiter, make_session, verify_password
from ..services import promptgen, store
from ..services.wizard import DEFAULTS
from ..templating import render

router = APIRouter(include_in_schema=False)


def _cookie_secure(request: Request) -> bool:
    return settings.cookie_secure or request.headers.get("x-forwarded-proto", request.url.scheme) == "https"


def _login_redirect(request: Request, user: User, to: str) -> RedirectResponse:
    resp = RedirectResponse(to, status_code=303)
    resp.set_cookie(settings.session_cookie_name, make_session(user.id), httponly=True, samesite="lax",
                    secure=_cookie_secure(request), max_age=settings.session_max_age_seconds)
    return resp


def _client(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    user = session_user(request, db)
    if user:
        return RedirectResponse("/", status_code=303)
    return render(request, "login.html", {"error": None, "user": None})


@router.post("/login", response_class=HTMLResponse)
def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    key = _client(request)
    if login_limiter.blocked(key):
        return render(request, "login.html", {"error": "Too many attempts. Try again in a few minutes.", "user": None}, status=429)
    user = db.query(User).filter(User.username == username.strip()).first()
    if not user or not verify_password(password, user.password_hash):
        login_limiter.fail(key)
        return render(request, "login.html", {"error": "Wrong username or password.", "user": None}, status=401)
    login_limiter.reset(key)
    return _login_redirect(request, user, "/account/password" if user.must_change_password else "/")


@router.post("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(settings.session_cookie_name)
    return resp


@router.get("/account/password", response_class=HTMLResponse)
def password_page(request: Request, db: Session = Depends(get_db)):
    user = session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    return render(request, "password.html", {"user": user, "error": None, "forced": user.must_change_password})


@router.post("/account/password", response_class=HTMLResponse)
def password_change(request: Request, current: str = Form(...), new: str = Form(...), confirm: str = Form(...),
                    db: Session = Depends(get_db)):
    user = session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    error = None
    if not verify_password(current, user.password_hash):
        error = "Current password is wrong."
    elif len(new) < 8:
        error = "Use at least 8 characters."
    elif new == "admin" or new == current:
        error = "Choose a new password that is not the default."
    elif new != confirm:
        error = "The two new passwords do not match."
    if error:
        return render(request, "password.html", {"user": user, "error": error, "forced": user.must_change_password}, status=400)
    user.password_hash = hash_password(new)
    user.must_change_password = False
    db.commit()
    return RedirectResponse("/?pw=1", status_code=303)


@router.get("/", response_class=HTMLResponse)
def home(request: Request, user: User = Depends(page_user), db: Session = Depends(get_db)):
    rows = db.query(PromptRecord).order_by(PromptRecord.updated_at.desc()).all()
    return render(request, "home.html", {"user": user, "prompts": rows, "active": "home"})


@router.get("/wizard", response_class=HTMLResponse)
def wizard(request: Request, edit: int | None = None, duplicate: int | None = None,
           user: User = Depends(page_user), db: Session = Depends(get_db)):
    initial = {**DEFAULTS, **store.wizard_defaults(db)}
    editing = None
    src = edit or duplicate
    if src:
        rec = db.get(PromptRecord, src)
        if not rec:
            raise HTTPException(404, "Prompt not found")
        initial = {**initial, **json.loads(rec.spec)}
        if edit:
            editing = rec.id
        else:
            initial["app_name"] = f"{initial['app_name']} copy"
    return render(request, "wizard.html", {"user": user, "initial": initial, "editing": editing, "active": "wizard"})


@router.get("/prompts/{pid}", response_class=HTMLResponse)
def prompt_view(pid: int, request: Request, user: User = Depends(page_user), db: Session = Depends(get_db)):
    rec = db.get(PromptRecord, pid)
    if not rec:
        raise HTTPException(404, "Prompt not found")
    spec = json.loads(rec.spec)
    return render(request, "prompt.html", {"user": user, "rec": rec, "ctx_name": promptgen.context_file_name(rec.tool),
                                            "active": "home"})


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, user: User = Depends(page_user), db: Session = Depends(get_db)):
    key = store.openai_key(db)
    return render(request, "settings.html", {
        "user": user, "active": "settings", "openai_set": bool(key), "openai_env": bool(settings.openai_api_key_env),
        "defaults": {**DEFAULTS, **store.wizard_defaults(db)},
    })


@router.get("/api/docs", response_class=HTMLResponse)
def api_docs(request: Request, user: User = Depends(page_user)):
    return render(request, "apidocs.html", {"user": user, "active": "docs"})
