from conftest import FlaskClient, get_test_client
from flask import url_for


client = get_test_client()
OK = 200


def test_dashboard(client: FlaskClient) -> None:
    response = client.get(url_for("dashboard"))
    assert response.status_code == OK


def test_settings(client: FlaskClient) -> None:
    response = client.get(url_for("settings"))
    assert response.status_code == OK


def test_docs(client: FlaskClient) -> None:
    response = client.get(url_for("docs"))
    assert response.status_code == OK
