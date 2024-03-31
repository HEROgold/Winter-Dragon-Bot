from typing import Any, Generator

import pytest

from flask import Flask
from flask.testing import FlaskClient


app = Flask(__name__)


@pytest.fixture()
def get_test_client() -> Generator[FlaskClient, Any, None]:
    with app.test_client() as client:
        yield client
