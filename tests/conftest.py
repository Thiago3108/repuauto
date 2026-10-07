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


CLAVE = "clave-segura-1"


@pytest.fixture()
def crear_cuenta(app):
    """Crea una cuenta con los roles de flask seed. Uso: crear_cuenta("vendedor")."""
    from app.auth.services import crear_usuario
    from app.cli import roles

    roles()

    def crear(rol="cliente", correo=None, activo=True):
        usuario = crear_usuario(correo or f"{rol}@repuauto.com", CLAVE, rol.capitalize(), rol)
        usuario.activo = activo
        db.session.commit()
        return usuario

    return crear


@pytest.fixture()
def iniciar_sesion(client):
    """Inicia sesión en el cliente de pruebas. Uso: iniciar_sesion(usuario)."""

    def iniciar(usuario, clave=CLAVE):
        return client.post("/auth/login", data={"correo": usuario.correo, "clave": clave})

    return iniciar
