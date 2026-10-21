"""Controlador del módulo Ventas (US-06 y US-08).

Las rutas reciben la petición, llaman a services.py y eligen la plantilla.
No consultan la base de datos directamente: eso es trabajo de services.py.
"""
from flask import render_template

from app.ventas import bp


@bp.get("/")
def index():
    return render_template(
        "en_construccion.html",
        modulo="Ventas",
        historia="US-06 y US-08",
        vistas="UI-05, UI-06 y UI-07",
    )
