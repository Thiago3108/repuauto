"""Comandos de consola del proyecto.

flask seed carga los datos iniciales: roles, estados de venta, categorías, marcas y el
primer administrador. Cada dueño agrega aquí la función de sus datos cuando crea sus
tablas, marcada con @semilla. Las funciones deben poder correr varias veces sin
duplicar nada: primero revisan si el dato ya existe.
"""
import os

import click

from app.auth import services as cuentas
from app.extensions import db
from app.models import Rol

SEMILLAS = []


def semilla(funcion):
    """Registra una función de datos iniciales para que flask seed la ejecute."""
    SEMILLAS.append(funcion)
    return funcion


@semilla
def roles():
    """Los tres roles de la matriz de acceso (decisión D3)."""
    for nombre in ("cliente", "vendedor", "administrador"):
        if not db.session.scalar(db.select(Rol).filter_by(nombre=nombre)):
            db.session.add(Rol(nombre=nombre))


@semilla
def primer_administrador():
    """La primera cuenta de administrador, con el correo y la clave del .env.

    Va después de roles(). Si el correo ya tiene cuenta, no hace nada: para cambiar la
    clave después, se hace desde la app, no volviendo a correr flask seed.
    """
    correo = os.environ.get("ADMIN_CORREO")
    clave = os.environ.get("ADMIN_CLAVE")
    if not correo or not clave:
        click.echo("  aviso: faltan ADMIN_CORREO o ADMIN_CLAVE en tu .env; no se creó el administrador.")
        return
    if not cuentas.contrasena_segura(clave):
        raise click.ClickException(
            "ADMIN_CLAVE debe tener más de 8 caracteres, al menos un número y un carácter especial."
        )
    if cuentas.buscar_por_correo(correo) is None:
        cuentas.crear_usuario(correo, clave, "Administrador", "administrador")


@click.command("seed")
def seed_command():
    """Carga los datos iniciales en la base de datos."""
    if not SEMILLAS:
        click.echo("Todavía no hay datos iniciales definidos.")
        return
    for funcion in SEMILLAS:
        funcion()
        click.echo(f"  listo: {funcion.__name__}")
    db.session.commit()
    click.echo("Datos iniciales cargados.")
