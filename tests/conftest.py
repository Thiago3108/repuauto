"""Piezas compartidas por todas las pruebas.

Cada prueba recibe una app con la configuración de pruebas (TEST_DATABASE_URL),
con las tablas recién creadas, y al terminar se borran. Así ninguna prueba
depende de lo que dejó otra.
"""
import pytest

from app import create_app
from app.extensions import db
from config import TestConfig


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
