import tempfile

import pytest

from app import create_app


@pytest.fixture()
def client():
    with tempfile.NamedTemporaryFile(suffix=".db") as database:
        app = create_app(database.name)
        app.config.update(TESTING=True)
        with app.test_client() as test_client:
            yield test_client


def test_register_success(client):
    response = client.post(
        "/api/register",
        json={"username": "tester01", "password": "secret123"},
    )

    assert response.status_code == 201
    assert response.get_json()["message"] == "注册成功"


def test_login_success(client):
    client.post(
        "/api/register",
        json={"username": "tester02", "password": "secret123"},
    )

    response = client.post(
        "/api/login",
        json={"username": "tester02", "password": "secret123"},
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == "登录成功"


def test_register_rejects_short_username_business_rule(client):
    response = client.post(
        "/api/register",
        json={"username": "abc", "password": "secret123"},
    )

    assert response.status_code == 400
    assert response.get_json()["message"] == "用户名长度不能少于6位"
