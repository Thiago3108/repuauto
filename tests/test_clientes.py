"""Pruebas de US-02: tabla cliente."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Cliente


def crear_cliente(cedula="1098765432", **datos):
    cliente = Cliente(cedula=cedula, nombres="Ana María", apellidos="Rueda Gómez", **datos)
    db.session.add(cliente)
    db.session.commit()
    return cliente


def test_un_cliente_de_mostrador_no_tiene_cuenta(app):
    cliente = crear_cliente()

    assert cliente.usuario is None
    assert cliente.telefono is None
    assert cliente.creado_en is not None
    assert cliente.nombre_completo == "Ana María Rueda Gómez"


def test_la_cedula_no_se_repite(app):
    crear_cliente(cedula="1098765432")

    with pytest.raises(IntegrityError):
        crear_cliente(cedula="1098765432")


def test_un_cliente_se_enlaza_con_su_cuenta(app, crear_cuenta):
    cuenta = crear_cuenta("cliente")

    cliente = crear_cliente(usuario=cuenta)

    assert cliente.id_usuario == cuenta.id_usuario
    assert cuenta.cliente is cliente


def test_una_cuenta_se_enlaza_a_un_solo_cliente(app, crear_cuenta):
    cuenta = crear_cuenta("cliente")
    crear_cliente(cedula="111", id_usuario=cuenta.id_usuario)

    with pytest.raises(IntegrityError):
        crear_cliente(cedula="222", id_usuario=cuenta.id_usuario)
