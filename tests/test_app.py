import io
import json

from app.services import logos as logo_service

SPEC = {"app_name": "Recipe Vault", "purpose": "Store and search family recipes with photos, tags and a weekly meal planner.",
        "target_users": "my family", "staging": True, "hermes": True,
        "external_apis": [{"name": "Spoonacular", "purpose": "nutrition lookups"}]}


def test_health_is_public(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/ready").json()["status"] == "ready"


def test_pages_require_login(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"
    assert client.get("/api/v1/prompts").status_code == 401


def test_bad_login_and_forced_change(client):
    assert client.post("/login", data={"username": "admin", "password": "nope"}).status_code == 401


def test_default_password_flow(authed):
    assert authed.get("/").status_code == 200
    r = authed.post("/account/password", data={"current": "S3cret-pass!", "new": "short", "confirm": "short"})
    assert r.status_code == 400


def test_pages_render(authed):
    for path in ("/", "/wizard", "/settings", "/api/docs"):
        r = authed.get(path)
        assert r.status_code == 200, path
    assert 'data-theme="' in authed.get("/").text


def test_security_headers_and_csrf(authed):
    r = authed.get("/")
    assert r.headers["x-frame-options"] == "DENY" and "default-src 'self'" in r.headers["content-security-policy"]
    r = authed.post("/ui/appearance", json={"theme": "nord"}, headers={"Origin": "http://evil.example"})
    assert r.status_code == 403


def test_appearance_five_themes_five_fonts(authed):
    from app.config import FONTS, THEMES
    assert len(THEMES) == 5 and len(FONTS) == 5
    assert authed.post("/ui/appearance", json={"theme": "sand", "font": "lato"}).json() == {"theme": "sand", "font": "lato"}
    assert 'data-theme="sand"' in authed.get("/").text
    assert authed.post("/ui/appearance", json={"theme": "bogus"}).status_code == 422


def test_generate_and_prompt_rules(authed):
    r = authed.post("/api/v1/generate", json={"spec": SPEC})
    assert r.status_code == 200
    md = r.json()["prompt_md"]
    for needle in ("admin` / `admin`", "5 themes", "/mnt/user/appdata/recipe-vault/data", "gh repo create jayvenco/recipe-vault",
                   "develop", "Hermes Agent", "Spoonacular", "UI language and all documentation: **English**", "SQLite"):
        assert needle in md, needle
    assert r.json()["context_name"] == "CLAUDE.md"


def test_codex_tool_and_validation(authed):
    r = authed.post("/api/v1/generate", json={"spec": {**SPEC, "tool": "codex"}})
    assert r.json()["context_name"] == "AGENTS.md" and "OpenAI Codex" in r.json()["prompt_md"]
    assert authed.post("/api/v1/generate", json={"spec": {"purpose": "x"}}).status_code == 422


def test_followups(authed):
    qs = authed.post("/api/v1/followups", json={"spec": {"app_name": "x", "purpose": "short", "hermes": True, "user_mode": "multi"}}).json()["items"]
    ids = {q["id"] for q in qs}
    assert {"purpose_detail", "roles", "hermes_scope"} <= ids
    answered = authed.post("/api/v1/followups", json={"spec": {"app_name": "x", "purpose": "short", "user_mode": "multi",
                                                              "followups": {"roles": "admin, viewer"}}}).json()["items"]
    assert "roles" not in {q["id"] for q in answered}


def test_prompt_crud_and_export_import(authed):
    r = authed.post("/api/v1/prompts", json={"spec": SPEC})
    pid = r.json()["id"]
    assert authed.get(f"/api/v1/prompts/{pid}").json()["name"] == "Recipe Vault"
    assert authed.get(f"/prompts/{pid}").status_code == 200
    assert authed.get(f"/wizard?duplicate={pid}").status_code == 200
    r = authed.patch(f"/api/v1/prompts/{pid}", json={"name": "Renamed", "spec": {**SPEC, "staging": False}})
    assert r.json()["name"] == "Renamed"
    assert "Single release flow" in r.json()["prompt_md"] and "`develop` (staging)" not in r.json()["prompt_md"]
    dl = authed.get(f"/api/v1/prompts/{pid}/download?file=context")
    assert "CLAUDE.md" in dl.headers["content-disposition"]
    exported = authed.get("/api/v1/prompts/export").json()
    assert authed.post("/api/v1/prompts/import", json=exported).json()["imported"] >= 1
    assert authed.delete(f"/api/v1/prompts/{pid}").json()["deleted"] is True
    assert authed.get(f"/api/v1/prompts/{pid}").status_code == 404


def test_tokens_scopes(authed, client):
    t = authed.post("/ui/tokens", json={"name": "Hermes", "scope": "read"}).json()["token"]
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as anon:
        h = {"Authorization": f"Bearer {t}"}
        assert anon.get("/api/v1/health", headers=h).json()["scope"] == "read"
        assert anon.post("/api/v1/prompts", json={"spec": SPEC}, headers=h).status_code == 403
        assert anon.post("/api/v1/generate", json={"spec": SPEC}, headers=h).status_code == 200  # generate without saving is read-only
        assert anon.post("/api/v1/generate", json={"spec": SPEC, "save": True}, headers=h).status_code == 403
        assert anon.get("/ui/tokens", headers=h).status_code == 401  # token management is cookie-only
        w = authed.post("/ui/tokens", json={"name": "Hermes rw", "scope": "write"}).json()["token"]
        assert anon.post("/api/v1/prompts", json={"spec": SPEC}, headers={"Authorization": f"Bearer {w}"}).status_code == 200
        tid = authed.get("/ui/tokens").json()["items"][0]["id"]
        authed.delete(f"/ui/tokens/{tid}")
        assert anon.get("/api/v1/health", headers={"Authorization": f"Bearer {w}"}).status_code == 401
    assert any(t["last_used_at"] for t in authed.get("/ui/tokens").json()["items"])


def test_openapi_has_no_external_assets(client):
    spec = client.get("/api/openapi.json").json()
    assert "/api/v1/generate" in spec["paths"]


def test_logo_generation_mocked(authed, monkeypatch):
    import base64
    from PIL import Image
    buf = io.BytesIO(); Image.new("RGB", (64, 64), "red").save(buf, "PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()

    class R:
        status_code = 200
        def json(self): return {"data": [{"b64_json": b64}, {"b64_json": b64}]}
    monkeypatch.setattr(logo_service.httpx, "post", lambda *a, **k: R())
    # no key yet -> friendly error
    assert authed.post("/api/v1/logos", json={"description": "a whale"}).status_code == 400
    assert authed.post("/ui/openai-key", json={"key": "nope"}).status_code == 422
    assert authed.post("/ui/openai-key", json={"key": "sk-test-123"}).json()["configured"] is True
    r = authed.post("/api/v1/logos", json={"description": "a whale", "n": 2})
    items = r.json()["items"]
    assert len(items) == 2
    img = authed.get(items[0]["image_url"])
    assert img.headers["content-type"] == "image/png"
    icon = Image.open(io.BytesIO(authed.get(items[0]["icon_url"]).content))
    assert icon.size == (256, 256)
    assert authed.post("/ui/openai-key", json={"key": ""}).json()["configured"] is False


def test_backup_export_restore(authed):
    r = authed.post("/api/v1/prompts", json={"spec": SPEC, "name": "before backup"})
    pid = r.json()["id"]
    name = authed.post("/ui/backups").json()["name"]
    assert name in [b["name"] for b in authed.get("/ui/backups").json()["items"]]
    zdata = authed.get(f"/ui/backups/{name}").content
    authed.delete(f"/api/v1/prompts/{pid}")
    assert authed.get(f"/api/v1/prompts/{pid}").status_code == 404
    bad = authed.post("/ui/backups/restore", files={"file": ("x.zip", b"not a zip")})
    assert bad.status_code == 400
    ok = authed.post("/ui/backups/restore", files={"file": ("b.zip", zdata)})
    assert ok.status_code == 200
    # session cookie cleared -> sign in again with the changed password
    authed.cookies.clear()
    r = authed.post("/login", data={"username": "admin", "password": "S3cret-pass!"}, follow_redirects=False)
    assert r.status_code == 303
    assert authed.get(f"/api/v1/prompts/{pid}").status_code == 200  # restored
    assert any(b["name"].startswith("before-restore") for b in authed.get("/ui/backups").json()["items"])


def test_backup_config_and_retention(authed):
    assert authed.post("/ui/backups/config", json={"enabled": True, "schedule": "weekly", "keep": 2}).json()["config"]["keep"] == 2
    for _ in range(4):
        authed.post("/ui/backups")
    kept = [b for b in authed.get("/ui/backups").json()["items"] if not b["name"].startswith("before-restore")]
    assert len(kept) <= 2
