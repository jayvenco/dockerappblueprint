from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from sqlalchemy import text

from .config import BASE_DIR, THEMES, settings
from .database import Base, SessionLocal, engine
from .deps import NeedLogin, NeedPasswordChange
from .models import User
from .routers import api, pages, ui
from .security import hash_password
from .services import backup

log = logging.getLogger("dab")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def seed_admin() -> None:
    with SessionLocal() as db:
        if db.query(User).count() == 0:
            theme = settings.default_theme if settings.default_theme in THEMES else "midnight"
            db.add(User(username=settings.default_username, password_hash=hash_password(settings.default_password),
                        must_change_password=True, theme=theme))
            db.commit()
            log.info("Created default account admin/admin (password change is required at first login)")


async def backup_scheduler() -> None:
    while True:
        try:
            path = await asyncio.to_thread(backup.run_due)
            if path:
                log.info("Automatic backup created: %s", path.name)
        except Exception:  # noqa: BLE001
            log.exception("Automatic backup failed")
        await asyncio.sleep(900)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(engine)
    seed_admin()
    task = asyncio.create_task(backup_scheduler())
    yield
    task.cancel()


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url="/api/openapi.json",
              description="REST API for DockerAppBlueprint. Authenticate with `Authorization: Bearer <token>`.")


@app.middleware("http")
async def protect(request: Request, call_next):
    # CSRF: cookie-authenticated state-changing requests must come from the same origin.
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and not request.headers.get("authorization"):
        origin = request.headers.get("origin")
        if origin:
            host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
            if origin.split("://", 1)[-1] != host:
                return JSONResponse({"detail": "Cross-origin request blocked"}, status_code=403)
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'none'",
    )
    return response


@app.exception_handler(NeedLogin)
async def _need_login(_r: Request, _e: NeedLogin):
    return RedirectResponse("/login", status_code=303)


@app.exception_handler(NeedPasswordChange)
async def _need_pw(_r: Request, _e: NeedPasswordChange):
    return RedirectResponse("/account/password", status_code=303)


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok", "version": settings.version}


@app.get("/ready", include_in_schema=False)
def ready():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ready"}


app.include_router(pages.router)
app.include_router(ui.router)
app.include_router(api.router)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
