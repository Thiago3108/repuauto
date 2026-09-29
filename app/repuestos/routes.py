"""Controlador del módulo Repuestos y stock (US-04).

Las rutas reciben la petición, llaman a services.py y eligen la plantilla.
No consultan la base de datos directamente: eso es trabajo de services.py.
"""
from flask import render_template

from app.repuestos import bp


@bp.get("/")
def index():
    return render_template(
        "en_construccion.html",
        modulo="Repuestos y stock",
        historia="US-04",
        vistas="UI-09 y UI-10",
    )
