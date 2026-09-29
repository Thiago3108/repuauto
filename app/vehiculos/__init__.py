"""Módulo Gestión de vehículos (US-03): vehículos y los repuestos compatibles con cada uno.

Este paquete es un blueprint: un minicontrolador con sus rutas bajo /vehiculos.
La fábrica create_app() solo lo registra, así que el dueño del módulo trabaja
en esta carpeta sin tocar las de los demás.
"""
from flask import Blueprint

bp = Blueprint("vehiculos", __name__, url_prefix="/vehiculos")

# Va al final para evitar la importación circular: routes.py importa bp de aquí.
from app.vehiculos import routes  # noqa: E402,F401
