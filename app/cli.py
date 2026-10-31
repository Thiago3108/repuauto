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
from app.models import Categoria, EstadoVenta, MarcaRepuesto, MarcaVehiculo, Rol
from app.models.venta import ESTADOS_DE_VENTA

MARCAS_VEHICULO = (
    "Chevrolet", "Renault", "Mazda", "Kia", "Toyota", "Nissan", "Hyundai",
    "Volkswagen", "Ford", "Suzuki", "Mitsubishi", "Honda",
)

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
def categorias_repuesto():
    """Crea categorías iniciales sin duplicar las existentes."""
    nombres = (
        "Motor",
        "Frenos",
        "Suspensión",
        "Sistema eléctrico",
        "Filtros",
    )

    for nombre in nombres:
        existe = db.session.scalar(
            db.select(Categoria.id_categoria).filter_by(nombre=nombre)
        )
        if existe is None:
            db.session.add(Categoria(nombre=nombre))

@semilla
def marcas_repuesto():
    """Crea marcas iniciales sin duplicar las existentes."""
    nombres = (
        "Bosch",
        "Denso",
        "NGK",
        "Gates",
        "Genérica",
    )

    for nombre in nombres:
        existe = db.session.scalar(
            db.select(MarcaRepuesto.id_marca_repuesto).filter_by(nombre=nombre)
        )
        if existe is None:
            db.session.add(MarcaRepuesto(nombre=nombre))

@semilla
def estados_venta():
    """Los estados de una venta (US-06): Pendiente, Completada y Cancelada."""
    for nombre in ESTADOS_DE_VENTA:
        if not db.session.scalar(db.select(EstadoVenta).filter_by(nombre=nombre)):
            db.session.add(EstadoVenta(nombre=nombre))


@semilla
def marcas_vehiculo():
    """Las marcas de carro más comunes (US-03). El administrador puede agregar más."""
    for nombre in MARCAS_VEHICULO:
        if not db.session.scalar(db.select(MarcaVehiculo).filter_by(nombre=nombre)):
            db.session.add(MarcaVehiculo(nombre=nombre))


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
