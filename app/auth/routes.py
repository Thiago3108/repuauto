"""Controlador del módulo Cuentas y acceso (US-01).

Las rutas reciben la petición, llaman a services.py y eligen la plantilla.
No consultan la base de datos directamente: eso es trabajo de services.py.
"""
from flask import render_template

from app.auth import bp


@bp.get("/")
def index():
    return render_template(
        "en_construccion.html",
        modulo="Cuentas y acceso",
        historia="US-01",
        vistas="UI-01, UI-02, UI-03 y UI-13",
    )
