"""Módulo Gestión de clientes (US-02): clientes de mostrador, búsqueda por nombre, cédula o teléfono y enlace de cuentas.

Este paquete es un blueprint: un minicontrolador con sus rutas bajo /clientes.
La fábrica create_app() solo lo registra, así que el dueño del módulo trabaja
en esta carpeta sin tocar las de los demás.
"""
from flask import Blueprint

bp = Blueprint("clientes", __name__, url_prefix="/clientes")

# Va al final para evitar la importación circular: routes.py importa bp de aquí.
from app.clientes import routes  # noqa: E402,F401
