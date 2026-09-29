"""Módulo Cuentas y acceso (US-01): registro de clientes, inicio de sesión, control de acceso por rol y cuentas de vendedor.

Este paquete es un blueprint: un minicontrolador con sus rutas bajo /auth.
La fábrica create_app() solo lo registra, así que el dueño del módulo trabaja
en esta carpeta sin tocar las de los demás.
"""
from flask import Blueprint

bp = Blueprint("auth", __name__, url_prefix="/auth")

# Va al final para evitar la importación circular: routes.py importa bp de aquí.
from app.auth import routes  # noqa: E402,F401
