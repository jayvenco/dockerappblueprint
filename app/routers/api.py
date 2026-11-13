"""REST API v1 for the web UI and for Hermes Agent (Bearer token or browser session)."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import Actor, api_actor, write_actor
from ..models import Logo, PromptRecord
from ..services import logos as logo_service
from ..services import promptgen, store
from ..services.wizard import DEFAULTS, IMPROVEMENTS, STEPS, followups, merge_spec, validate_spec

router = APIRouter(prefix="/api/v1", tags=["v1"])


class SpecIn(BaseModel):
    spec: dict[str, Any] = Field(default_factory=dict, description="Wizard answers; see GET /wizard/schema for keys")
    name: str | None = None
    save: bool = False


class PromptPatch(BaseModel):
    name: str | None = None
    spec: dict[str, Any] | None = None


class LogoIn(BaseModel):
    description: str
    n: int = 3
    prompt_id: int | None = None


def _record(p: PromptRecord, full: bool = True) -> dict[str, Any]:
    spec = json.loads(p.spec or "{}")
    out = {"id": p.id, "name": p.name, "tool": p.tool, "created_at": p.created_at.isoformat(),
           "updated_at": p.updated_at.isoformat(), "app_name": spec.get("app_name", "")}
    if full:
        out.update(spec=spec, prompt_md=p.prompt_md, context_md=p.context_md,
                   context_name=promptgen.context_file_name(p.tool))
    return out


def _generate(spec: dict[str, Any]) -> dict[str, Any]:
    merged = merge_spec(spec)
    errors = validate_spec(merged)
    if errors:
        raise HTTPException(422, {"errors": errors})
    return promptgen.build_prompt(merged)


def _logo(l: Logo) -> dict[str, Any]:
    return {"id": l.id, "description": l.description, "prompt_id": l.prompt_id,
            "created_at": l.created_at.isoformat(), "image_url": f"/api/v1/logos/{l.id}/image.png",
            "icon_url": f"/api/v1/logos/{l.id}/icon.png"}


@router.get("/health", summary="Health and auth check")
def health(actor: Actor = Depends(api_actor)):
    return {"status": "ok", "auth": "ok", "scope": actor.scope, "version": settings.version}


@router.get("/version")
def version(actor: Actor = Depends(api_actor)):
    return {"app": settings.app_name, "version": settings.version}


@router.get("/wizard/schema", summary="Wizard steps, defaults and improvement suggestions")
def wizard_schema(actor: Actor = Depends(api_actor), db: Session = Depends(get_db)):
    defaults = {**DEFAULTS, **store.wizard_defaults(db)}
    return {"steps": STEPS, "defaults": defaults, "improvements": IMPROVEMENTS}


@router.get("/suggestions", summary="List improvement suggestions")
def suggestions(actor: Actor = Depends(api_actor)):
    return {"items": IMPROVEMENTS}


@router.post("/followups", summary="Follow-up questions for unclear or incomplete answers")
def followups_ep(body: SpecIn, actor: Actor = Depends(api_actor)):
    return {"items": followups(body.spec)}


@router.post("/generate", summary="Run the wizard non-interactively and return the prompt")
def generate(body: SpecIn, actor: Actor = Depends(api_actor), db: Session = Depends(get_db)):
    result = _generate(body.spec)
    out = {k: result[k] for k in ("slug", "prompt_md", "context_md", "context_name", "open_questions")}
    out["spec"] = result["spec"]
    if body.save:
        actor.require_write()
        rec = PromptRecord(name=body.name or result["spec"]["app_name"], tool=result["spec"]["tool"],
                           spec=json.dumps(result["spec"]), prompt_md=result["prompt_md"],
                           context_md=result["context_md"])
        db.add(rec)
        db.commit()
        out["id"] = rec.id
    return out


@router.get("/prompts")
def list_prompts(limit: int = 100, offset: int = 0, actor: Actor = Depends(api_actor), db: Session = Depends(get_db)):
    limit = max(1, min(500, limit))
    q = db.query(PromptRecord)
    return {"items": [_record(p, False) for p in q.order_by(PromptRecord.updated_at.desc()).limit(limit).offset(offset)],
            "total": q.count(), "limit": limit, "offset": offset}


@router.post("/prompts", summary="Create and save a prompt from a wizard spec")
def create_prompt(body: SpecIn, actor: Actor = Depends(write_actor), db: Session = Depends(get_db)):
    result = _generate(body.spec)
    rec = PromptRecord(name=body.name or result["spec"]["app_name"], tool=result["spec"]["tool"],
                       spec=json.dumps(result["spec"]), prompt_md=result["prompt_md"], context_md=result["context_md"])
    db.add(rec)
    db.commit()
    return {**_record(rec), "open_questions": result["open_questions"]}


# Fixed paths before /prompts/{id}
@router.get("/prompts/export", summary="Export all saved prompts as JSON")
def export_prompts(actor: Actor = Depends(api_actor), db: Session = Depends(get_db)):
    items = [_record(p) for p in db.query(PromptRecord).order_by(PromptRecord.id)]
    return {"app": settings.app_name, "version": settings.version, "items": items}


@router.post("/prompts/import", summary="Import prompts from an export")
def import_prompts(payload: dict[str, Any], actor: Actor = Depends(write_actor), db: Session = Depends(get_db)):
    count = 0
    for item in payload.get("items", []):
        spec = item.get("spec")
        if not isinstance(spec, dict):
            continue
        try:
            result = _generate(spec)
        except HTTPException:
            continue
        db.add(PromptRecord(name=str(item.get("name") or result["spec"]["app_name"])[:120], tool=result["spec"]["tool"],
                            spec=json.dumps(result["spec"]), prompt_md=result["prompt_md"], context_md=result["context_md"]))
        count += 1
    db.commit()
    return {"imported": count}


def _get(db: Session, pid: int) -> PromptRecord:
    rec = db.get(PromptRecord, pid)
    if not rec:
        raise HTTPException(404, "Prompt not found")
    return rec


@router.get("/prompts/{pid}")
def get_prompt(pid: int, actor: Actor = Depends(api_actor), db: Session = Depends(get_db)):
    rec = _get(db, pid)
    return {**_record(rec), "open_questions": followups(json.loads(rec.spec))}


@router.patch("/prompts/{pid}")
def patch_prompt(pid: int, body: PromptPatch, actor: Actor = Depends(write_actor), db: Session = Depends(get_db)):
    rec = _get(db, pid)
    if body.spec is not None:
        result = _generate(body.spec)
        rec.spec, rec.tool = json.dumps(result["spec"]), result["spec"]["tool"]
        rec.prompt_md, rec.context_md = result["prompt_md"], result["context_md"]
    if body.name:
        rec.name = body.name[:120]
    db.commit()
    return _record(rec)


@router.delete("/prompts/{pid}")
def delete_prompt(pid: int, actor: Actor = Depends(write_actor), db: Session = Depends(get_db)):
    rec = _get(db, pid)
    db.delete(rec)
    db.commit()
    return {"deleted": True, "id": pid}


@router.get("/prompts/{pid}/download", summary="Download the prompt or context file as Markdown")
def download(pid: int, file: str = "prompt", actor: Actor = Depends(api_actor), db: Session = Depends(get_db)):
    rec = _get(db, pid)
    slug = promptgen.slugify(json.loads(rec.spec).get("app_name", "prompt"))
    if file == "context":
        body, name = rec.context_md, promptgen.context_file_name(rec.tool)
    else:
        body, name = rec.prompt_md, f"{slug}-build-prompt.md"
    return Response(body, media_type="text/markdown; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.post("/logos", summary="Generate logo variants with OpenAI")
def create_logos(body: LogoIn, actor: Actor = Depends(write_actor), db: Session = Depends(get_db)):
    try:
        made = logo_service.generate(db, body.description, body.n, body.prompt_id)
    except logo_service.LogoError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"items": [_logo(l) for l in made]}


@router.get("/logos")
def list_logos(actor: Actor = Depends(api_actor), db: Session = Depends(get_db)):
    return {"items": [_logo(l) for l in db.query(Logo).order_by(Logo.id.desc()).limit(60)]}


def _get_logo(db: Session, lid: int) -> Logo:
    logo = db.get(Logo, lid)
    if not logo:
        raise HTTPException(404, "Logo not found")
    return logo


@router.get("/logos/{lid}/image.png")
def logo_image(lid: int, actor: Actor = Depends(api_actor), db: Session = Depends(get_db)):
    from ..config import LOGO_DIR
    logo = _get_logo(db, lid)
    return Response((LOGO_DIR / logo.filename).read_bytes(), media_type="image/png",
                    headers={"Content-Disposition": f'inline; filename="logo-{lid}.png"'})


@router.get("/logos/{lid}/icon.png", summary="256x256 icon for the Unraid template")
def logo_icon(lid: int, actor: Actor = Depends(api_actor), db: Session = Depends(get_db)):
    return Response(logo_service.icon_bytes(_get_logo(db, lid)), media_type="image/png",
                    headers={"Content-Disposition": f'inline; filename="icon-{lid}.png"'})


@router.delete("/logos/{lid}")
def delete_logo(lid: int, actor: Actor = Depends(write_actor), db: Session = Depends(get_db)):
    logo_service.delete(db, _get_logo(db, lid))
    return {"deleted": True, "id": lid}
