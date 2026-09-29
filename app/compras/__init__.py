"""Módulo Proveedores y compras (US-09): proveedores y compras que suman al stock.

Este paquete es un blueprint: un minicontrolador con sus rutas bajo /compras.
La fábrica create_app() solo lo registra, así que el dueño del módulo trabaja
en esta carpeta sin tocar las de los demás.
"""
from flask import Blueprint

bp = Blueprint("compras", __name__, url_prefix="/compras")

# Va al final para evitar la importación circular: routes.py importa bp de aquí.
from app.compras import routes  # noqa: E402,F401
