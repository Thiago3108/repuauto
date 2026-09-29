"""Pruebas del esqueleto: la app arranca, cada módulo responde y hay base de datos."""
import pytest
from sqlalchemy import text

from app.extensions import db
from app.menu import MENU

MODULOS = ["auth", "clientes", "vehiculos", "repuestos", "catalogo", "ventas", "reportes", "compras"]


def test_inicio_responde(client):
    respuesta = client.get("/")
    assert respuesta.status_code == 200
    assert "RepuAuto" in respuesta.get_data(as_text=True)


@pytest.mark.parametrize("modulo", MODULOS)
def test_cada_modulo_responde(client, modulo):
    assert client.get(f"/{modulo}/").status_code == 200


def test_el_menu_enlaza_a_todos_los_modulos():
    assert {item["endpoint"].split(".")[0] for item in MENU} == set(MODULOS)


def test_hay_conexion_con_la_base_de_datos(app):
    assert db.session.execute(text("SELECT 1")).scalar() == 1
