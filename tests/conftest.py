import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="dab-test-")
os.environ["DATA_DIR"] = _tmp

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def authed(client):
    """Signed-in client with the default password already changed."""
    r = client.post("/login", data={"username": "admin", "password": "admin"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/account/password"
    r = client.post("/account/password", data={"current": "admin", "new": "S3cret-pass!", "confirm": "S3cret-pass!"},
                    follow_redirects=False)
    assert r.status_code == 303
    return client
