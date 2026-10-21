"""Controlador del módulo Proveedores y compras (US-09).

Las rutas reciben la petición, llaman a services.py y eligen la plantilla.
No consultan la base de datos directamente: eso es trabajo de services.py.
"""
from flask import render_template

from app.compras import bp


@bp.get("/")
def index():
    return render_template(
        "en_construccion.html",
        modulo="Proveedores y compras",
        historia="US-09",
        vistas="UI-14",
    )
