"""Logo generation through the OpenAI images API."""
from __future__ import annotations

import base64
import io
import uuid

import httpx
from PIL import Image
from sqlalchemy.orm import Session

from ..config import LOGO_DIR, settings
from ..models import Logo
from . import store


class LogoError(Exception):
    pass


def build_prompt(description: str) -> str:
    return (
        f"App icon / logo for a self-hosted web app. {description.strip()}. "
        "Simple, bold, centered symbol on a clean background, flat vector style, "
        "readable at 64px, no text or letters, square composition."
    )


def generate(db: Session, description: str, n: int = 3, prompt_id: int | None = None) -> list[Logo]:
    key = store.openai_key(db)
    if not key:
        raise LogoError("No OpenAI API key configured. Add one in Settings or set OPENAI_API_KEY.")
    if not description.strip():
        raise LogoError("Describe the logo first.")
    n = max(1, min(4, n))
    model = settings.openai_image_model
    payload: dict = {"model": model, "prompt": build_prompt(description), "n": n, "size": "1024x1024"}
    if not model.startswith("gpt-image"):
        payload["response_format"] = "b64_json"
    try:
        r = httpx.post(
            f"{settings.openai_base_url}/images/generations",
            headers={"Authorization": f"Bearer {key}"},
            json=payload,
            timeout=180,
        )
    except httpx.HTTPError as exc:
        raise LogoError(f"Could not reach OpenAI: {exc.__class__.__name__}") from exc
    if r.status_code != 200:
        try:
            msg = r.json().get("error", {}).get("message", r.text[:200])
        except ValueError:
            msg = r.text[:200]
        raise LogoError(f"OpenAI error ({r.status_code}): {msg}")
    logos: list[Logo] = []
    for item in r.json().get("data", []):
        raw = None
        if item.get("b64_json"):
            raw = base64.b64decode(item["b64_json"])
        elif item.get("url"):
            raw = httpx.get(item["url"], timeout=60).content
        if not raw:
            continue
        try:
            img = Image.open(io.BytesIO(raw)).convert("RGBA")
        except Exception as exc:  # noqa: BLE001
            raise LogoError("OpenAI returned an image that could not be read.") from exc
        name = f"{uuid.uuid4().hex[:12]}.png"
        img.save(LOGO_DIR / name, "PNG")
        logo = Logo(prompt_id=prompt_id, description=description.strip(), filename=name)
        db.add(logo)
        logos.append(logo)
    db.commit()
    if not logos:
        raise LogoError("OpenAI returned no images.")
    return logos


def icon_bytes(logo: Logo, size: int = 256) -> bytes:
    img = Image.open(LOGO_DIR / logo.filename).convert("RGBA").resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def delete(db: Session, logo: Logo) -> None:
    (LOGO_DIR / logo.filename).unlink(missing_ok=True)
    db.delete(logo)
    db.commit()
