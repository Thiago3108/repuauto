"""Módulo Catálogo de repuestos (US-05): catálogo con filtro por marca, línea y año del vehículo.

Este paquete es un blueprint: un minicontrolador con sus rutas bajo /catalogo.
La fábrica create_app() solo lo registra, así que el dueño del módulo trabaja
en esta carpeta sin tocar las de los demás.
"""
from flask import Blueprint

bp = Blueprint("catalogo", __name__, url_prefix="/catalogo")

# Va al final para evitar la importación circular: routes.py importa bp de aquí.
from app.catalogo import routes  # noqa: E402,F401
