import pytest

import app


@pytest.fixture
def client():
    client = app.app.test_client()
    yield client


def test_app_root(client):
    response = client.get('/')
    assert response.status_code == 200


def test_app_listmodules(client):
    response = client.get('/listmodules')
    assert response.status_code == 200


def test_app_fetchdata(client):
    response = client.get('/fetchdata')
    assert response.status_code == 200
