import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.db_models import User
from app.main import app


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)


@pytest.fixture
def client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _register(client, username, password="secret123"):
    response = client.post(
        "/api/auth/register", json={"username": username, "password": password}
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _promote(session_factory, username):
    db = session_factory()
    try:
        db.query(User).filter(User.username == username).update({"role": "admin"})
        db.commit()
    finally:
        db.close()


@pytest.fixture
def auth_headers(client):
    return _register(client, "alice")


@pytest.fixture
def admin_headers(client, session_factory):
    _register(client, "boss")
    _promote(session_factory, "boss")
    # Re-login so the returned token reflects the admin role.
    login = client.post("/api/auth/login", json={"username": "boss", "password": "secret123"})
    assert login.json()["role"] == "admin"
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_register_rejects_duplicate_username(client):
    payload = {"username": "alice", "password": "secret123"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json=payload).status_code == 409


def test_login_flow(client):
    client.post("/api/auth/register", json={"username": "bob", "password": "secret123"})

    ok = client.post("/api/auth/login", json={"username": "bob", "password": "secret123"})
    assert ok.status_code == 200
    assert ok.json()["username"] == "bob"
    assert ok.json()["role"] == "user"  # public registration never grants admin

    bad = client.post("/api/auth/login", json={"username": "bob", "password": "wrong"})
    assert bad.status_code == 401


def test_analyses_require_auth(client):
    assert client.get("/api/analyses").status_code == 401


def test_upload_analyze_and_fetch(client, auth_headers, sky130_report):
    response = client.post(
        "/api/analyses",
        headers=auth_headers,
        files={"file": ("report.txt", sky130_report.encode(), "text/plain")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["result"]["summary"]["violated_paths"] == 1
    analysis_id = body["id"]

    listing = client.get("/api/analyses", headers=auth_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    detail = client.get(f"/api/analyses/{analysis_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["filename"] == "report.txt"

    assert client.delete(f"/api/analyses/{analysis_id}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/analyses/{analysis_id}", headers=auth_headers).status_code == 404


def test_upload_rejects_unparseable_report(client, auth_headers):
    response = client.post(
        "/api/analyses",
        headers=auth_headers,
        files={"file": ("junk.txt", b"not a timing report", "text/plain")},
    )
    assert response.status_code == 422


def test_users_cannot_see_each_others_analyses(client, auth_headers, basic_report):
    created = client.post(
        "/api/analyses",
        headers=auth_headers,
        files={"file": ("report.txt", basic_report.encode(), "text/plain")},
    )
    analysis_id = created.json()["id"]

    other = client.post(
        "/api/auth/register", json={"username": "mallory", "password": "secret123"}
    )
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}

    assert client.get(f"/api/analyses/{analysis_id}", headers=other_headers).status_code == 404
    assert client.get("/api/analyses", headers=other_headers).json() == []


# ---------- admin & role-based access ----------

def test_normal_user_cannot_reach_admin_routes(client, auth_headers):
    for path in ("/api/admin/users", "/api/admin/analyses", "/api/admin/stats",
                 "/api/admin/api-keys"):
        assert client.get(path, headers=auth_headers).status_code == 403


def test_admin_lists_all_users_with_counts(client, admin_headers, auth_headers, basic_report):
    client.post(
        "/api/analyses",
        headers=auth_headers,
        files={"file": ("r.txt", basic_report.encode(), "text/plain")},
    )
    users = client.get("/api/admin/users", headers=admin_headers).json()
    by_name = {u["username"]: u for u in users}
    assert by_name["boss"]["role"] == "admin"
    assert by_name["alice"]["role"] == "user"
    assert by_name["alice"]["analysis_count"] == 1


def test_admin_can_view_and_delete_any_analysis(client, admin_headers, auth_headers, basic_report):
    created = client.post(
        "/api/analyses",
        headers=auth_headers,
        files={"file": ("r.txt", basic_report.encode(), "text/plain")},
    )
    analysis_id = created.json()["id"]

    listed = client.get("/api/admin/analyses", headers=admin_headers).json()
    assert any(a["id"] == analysis_id and a["username"] == "alice" for a in listed)

    assert client.delete(f"/api/admin/analyses/{analysis_id}", headers=admin_headers).status_code == 204
    assert client.get(f"/api/analyses/{analysis_id}", headers=auth_headers).status_code == 404


def test_admin_user_management(client, admin_headers):
    created = client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={"username": "newbie", "password": "secret123", "role": "user"},
    )
    assert created.status_code == 201
    uid = created.json()["id"]

    # promote, then demote
    promoted = client.patch(f"/api/admin/users/{uid}", headers=admin_headers, json={"role": "admin"})
    assert promoted.json()["role"] == "admin"

    # new user can now log in as admin
    login = client.post("/api/auth/login", json={"username": "newbie", "password": "secret123"})
    assert login.json()["role"] == "admin"

    assert client.delete(f"/api/admin/users/{uid}", headers=admin_headers).status_code == 204


def test_admin_cannot_delete_or_demote_self(client, admin_headers):
    users = client.get("/api/admin/users", headers=admin_headers).json()
    me = next(u for u in users if u["username"] == "boss")
    assert client.delete(f"/api/admin/users/{me['id']}", headers=admin_headers).status_code == 400
    demote = client.patch(f"/api/admin/users/{me['id']}", headers=admin_headers, json={"role": "user"})
    assert demote.status_code == 400


def test_api_key_pool_flow(client, admin_headers, auth_headers):
    # admin adds a key
    created = client.post(
        "/api/admin/api-keys",
        headers=admin_headers,
        json={"label": "Team key", "secret": "gsk_supersecretvalue"},
    )
    assert created.status_code == 201
    assert created.json()["masked"].endswith("alue")

    # user sees it in the pool but never the secret
    options = client.get("/api/api-keys", headers=auth_headers).json()
    assert len(options) == 1
    assert options[0]["label"] == "Team key"
    assert "secret" not in options[0]

    # user cannot manage the pool
    assert client.get("/api/admin/api-keys", headers=auth_headers).status_code == 403

    # disabling a key hides it from the user pool
    key_id = created.json()["id"]
    client.patch(f"/api/admin/api-keys/{key_id}", headers=admin_headers, json={"is_active": False})
    assert client.get("/api/api-keys", headers=auth_headers).json() == []


def test_explain_rejects_unknown_key(client, auth_headers, sky130_report):
    created = client.post(
        "/api/analyses",
        headers=auth_headers,
        files={"file": ("r.txt", sky130_report.encode(), "text/plain")},
    )
    analysis_id = created.json()["id"]
    # No key in the pool and a bogus id -> 400, not a crash or a Groq call.
    resp = client.post(
        f"/api/analyses/{analysis_id}/paths/0/explain",
        headers=auth_headers,
        json={"api_key_id": 999},
    )
    assert resp.status_code == 400


def _upload(client, headers, name, text):
    response = client.post(
        "/api/analyses",
        headers=headers,
        files={"file": (name, text.encode(), "text/plain")},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_upload_returns_groups_and_rule_ids(client, auth_headers, adder_before):
    _upload(client, auth_headers, "adder_before.txt", adder_before)
    listing = client.get("/api/analyses", headers=auth_headers).json()
    detail = client.get(f"/api/analyses/{listing[0]['id']}", headers=auth_headers).json()

    assert detail["result"]["groups"][0]["kind"] == "shared_logic"
    first_fix = next(p for p in detail["result"]["paths"] if p["path"]["status"] == "VIOLATED")
    assert first_fix["diagnosis"]["suggestions"][0]["rule_id"]


def test_compare_two_analyses(client, auth_headers, adder_before, adder_after):
    base = _upload(client, auth_headers, "before.txt", adder_before)
    new = _upload(client, auth_headers, "after.txt", adder_after)

    response = client.get(f"/api/analyses/compare?base_id={base}&new_id={new}", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["base_filename"] == "before.txt"
    assert body["wns_before"] == -0.83 and body["wns_after"] == -0.47
    assert len(body["fixed"]) == 2


def test_compare_cannot_use_someone_elses_analysis(client, auth_headers, adder_before):
    mine = _upload(client, auth_headers, "mine.txt", adder_before)
    other = _register(client, "mallory")
    theirs = _upload(client, other, "theirs.txt", adder_before)

    response = client.get(f"/api/analyses/compare?base_id={mine}&new_id={theirs}", headers=auth_headers)
    assert response.status_code == 404


def test_analysis_saved_before_groups_existed_still_loads(client, auth_headers, session_factory, sky130_report):
    """Old rows in the database have no `groups` / `rule_id`; they must still open."""
    import json

    from app.db_models import Analysis

    analysis_id = _upload(client, auth_headers, "old.txt", sky130_report)
    db = session_factory()
    try:
        row = db.query(Analysis).filter(Analysis.id == analysis_id).one()
        data = json.loads(row.result_json)
        data.pop("groups")
        for p in data["paths"]:
            for s in p["diagnosis"]["suggestions"]:
                s.pop("rule_id")
        row.result_json = json.dumps(data)
        db.commit()
    finally:
        db.close()

    response = client.get(f"/api/analyses/{analysis_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["result"]["groups"] == []


def _fake_groq(monkeypatch, text):
    import requests

    class Reply:
        status_code = 200
        ok = True

        def json(self):
            return {"choices": [{"message": {"content": text}}]}

    monkeypatch.setattr(requests, "post", lambda *a, **k: Reply())


def test_explain_flags_numbers_missing_from_the_data(client, auth_headers, sky130_report, monkeypatch):
    from app import config

    monkeypatch.setattr(config, "GROQ_API_KEY", "test-key")
    _fake_groq(monkeypatch, "The path misses by 0.18 ns and runs at 900 MHz.")
    analysis_id = _upload(client, auth_headers, "r.txt", sky130_report)

    # Index 1 is the violated path in this report.
    response = client.post(
        f"/api/analyses/{analysis_id}/paths/1/explain", headers=auth_headers, json={}
    )
    assert response.status_code == 200
    assert response.json()["unverified_numbers"] == ["900"]
