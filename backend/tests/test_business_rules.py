import sqlite3
from contextlib import closing
import pytest
from backend.app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(str(tmp_path / "auth.db"), enable_demo=False)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_register_and_login(client):
    payload = {"username": "tester01", "password": "secret123"}
    register = client.post("/api/register", json=payload)
    assert register.status_code == 201
    assert register.get_json()["message"] == "注册成功"
    login = client.post("/api/login", json=payload)
    assert login.status_code == 200
    assert login.get_json()["message"] == "登录成功"
    assert "password_hash" not in login.get_json()["user"]


def test_duplicate_and_wrong_password(client):
    payload = {"username": "tester01", "password": "secret123"}
    assert client.post("/api/register", json=payload).status_code == 201
    assert client.post("/api/register", json=payload).status_code == 409
    assert client.post("/api/login", json={**payload, "password": "wrong123"}).status_code == 401


@pytest.mark.parametrize("payload", [None, [], 5, {"username": []},
    {"username": "tester01", "password": 123}, {"username": "u" * 129, "password": "secret123"}])
@pytest.mark.parametrize("endpoint", ["/api/register", "/api/login"])
def test_invalid_json_returns_400(client, payload, endpoint):
    assert client.post(endpoint, json=payload).status_code == 400


def test_injected_bug_and_fixed_mode(tmp_path):
    payload = {"username": "abc", "password": "secret123"}
    for injected, expected in [(True, 201), (False, 400)]:
        app = create_app(str(tmp_path / f"{injected}.db"), inject_bug=injected, enable_demo=False)
        with app.test_client() as client:
            assert client.post("/api/register", json=payload).status_code == expected
            assert client.get("/api/health").get_json()["inject_bug"] is injected
        with closing(sqlite3.connect(app.config["DATABASE"])) as database:
            stored = database.execute("SELECT password_hash FROM users").fetchone()
            assert (stored and stored[0] != payload["password"]) if injected else stored is None
