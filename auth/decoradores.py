"""Control de acceso por rol (US-01 T3), para que cada módulo proteja sus vistas.

Uso, en el routes.py de cualquier módulo:

    from app.auth.decoradores import rol_requerido

    @bp.get("/")
    @rol_requerido("vendedor", "administrador")
    def index():
        ...

Los roles de cada vista están en app/menu.py (decisión D3). Quien no ha iniciado sesión
va a la pantalla de login; quien no tiene el rol recibe un 403.
"""
from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def rol_requerido(*roles):
    def decorador(vista):
        @wraps(vista)
        @login_required
        def envoltura(*args, **kwargs):
            if not current_user.tiene_rol(*roles):
                abort(403)
            return vista(*args, **kwargs)

        return envoltura

    return decorador
