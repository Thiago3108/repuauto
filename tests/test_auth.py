"""Pruebas de US-01: tablas rol y usuario, y los roles de flask seed."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.cli import roles
from app.extensions import db
from app.models import Rol, Usuario


def crear_usuario(correo="ana@correo.com", rol="cliente"):
    usuario = Usuario(
        correo=correo,
        contrasena_hash="hash-de-prueba",
        nombre="Ana",
        rol=Rol(nombre=rol),
    )
    db.session.add(usuario)
    db.session.commit()
    return usuario


def test_la_semilla_crea_los_tres_roles_sin_duplicar(app):
    roles()
    roles()
    db.session.commit()

    nombres = db.session.scalars(db.select(Rol.nombre)).all()
    assert sorted(nombres) == ["administrador", "cliente", "vendedor"]


def test_un_usuario_nuevo_queda_activo_y_con_fecha(app):
    usuario = crear_usuario()

    assert usuario.activo is True
    assert usuario.creado_en is not None
    assert usuario.rol.nombre == "cliente"


def test_el_correo_no_se_repite(app):
    crear_usuario(correo="ana@correo.com", rol="cliente")

    with pytest.raises(IntegrityError):
        crear_usuario(correo="ana@correo.com", rol="vendedor")


def test_el_nombre_del_rol_no_se_repite(app):
    db.session.add(Rol(nombre="cliente"))
    db.session.commit()

    db.session.add(Rol(nombre="cliente"))
    with pytest.raises(IntegrityError):
        db.session.commit()
