"""Controlador del módulo Gestión de vehículos (US-03).

Las rutas reciben la petición, llaman a services.py y eligen la plantilla.
No consultan la base de datos directamente: eso es trabajo de services.py.
"""
from flask import render_template

from app.vehiculos import bp


@bp.get("/")
def index():
    return render_template(
        "en_construccion.html",
        modulo="Gestión de vehículos",
        historia="US-03",
        vistas="UI-11",
    )
