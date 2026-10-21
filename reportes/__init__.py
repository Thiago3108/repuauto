"""Módulo Reportes (US-07): reportes de ventas, inventario y clientes.

Este paquete es un blueprint: un minicontrolador con sus rutas bajo /reportes.
La fábrica create_app() solo lo registra, así que el dueño del módulo trabaja
en esta carpeta sin tocar las de los demás.
"""
from flask import Blueprint

bp = Blueprint("reportes", __name__, url_prefix="/reportes")

# Va al final para evitar la importación circular: routes.py importa bp de aquí.
from app.reportes import routes  # noqa: E402,F401
