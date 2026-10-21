"""Módulo Repuestos y stock (US-04): repuestos, ajustes de stock y alertas de stock bajo.

Este paquete es un blueprint: un minicontrolador con sus rutas bajo /repuestos.
La fábrica create_app() solo lo registra, así que el dueño del módulo trabaja
en esta carpeta sin tocar las de los demás.
"""
from flask import Blueprint

bp = Blueprint("repuestos", __name__, url_prefix="/repuestos")

# Va al final para evitar la importación circular: routes.py importa bp de aquí.
from app.repuestos import routes  # noqa: E402,F401
