"""Comandos de consola del proyecto.

flask seed carga los datos iniciales: roles, estados de venta, categorías, marcas y el
primer administrador. Cada dueño agrega aquí la función de sus datos cuando crea sus
tablas, marcada con @semilla. Las funciones deben poder correr varias veces sin
duplicar nada: primero revisan si el dato ya existe.
"""
import click

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
