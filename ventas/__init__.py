"""Módulo Ventas (US-06 y US-08): registro de ventas con verificación de stock, estados de la venta e historial del cliente.

Este paquete es un blueprint: un minicontrolador con sus rutas bajo /ventas.
La fábrica create_app() solo lo registra, así que el dueño del módulo trabaja
en esta carpeta sin tocar las de los demás.
"""
from flask import Blueprint

bp = Blueprint("ventas", __name__, url_prefix="/ventas")

# Va al final para evitar la importación circular: routes.py importa bp de aquí.
from app.ventas import routes  # noqa: E402,F401
