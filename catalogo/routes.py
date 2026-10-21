"""Controlador del módulo Catálogo de repuestos (US-05).

Las rutas reciben la petición, llaman a services.py y eligen la plantilla.
No consultan la base de datos directamente: eso es trabajo de services.py.
"""
from flask import render_template

from app.catalogo import bp


@bp.get("/")
def index():
    return render_template(
        "en_construccion.html",
        modulo="Catálogo de repuestos",
        historia="US-05",
        vistas="UI-04",
    )
