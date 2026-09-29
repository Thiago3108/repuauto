"""Controlador del módulo Gestión de clientes (US-02).

Las rutas reciben la petición, llaman a services.py y eligen la plantilla.
No consultan la base de datos directamente: eso es trabajo de services.py.
"""
from flask import render_template

from app.clientes import bp


@bp.get("/")
def index():
    return render_template(
        "en_construccion.html",
        modulo="Gestión de clientes",
        historia="US-02",
        vistas="UI-08",
    )
