"""Controlador del módulo Reportes (US-07).

Las rutas reciben la petición, llaman a services.py y eligen la plantilla.
No consultan la base de datos directamente: eso es trabajo de services.py.
"""
from flask import render_template

from app.reportes import bp


@bp.get("/")
def index():
    return render_template(
        "en_construccion.html",
        modulo="Reportes",
        historia="US-07",
        vistas="UI-12",
    )
