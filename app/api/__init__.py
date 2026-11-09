"""API REST de RepuAuto: entrega las compras y ventas en JSON a otros sistemas.

Es la parte de la integración entre sedes: el aplicativo consolidador pide aquí las
facturas de esta sede y las junta con las de la otra. Las rutas van bajo /api.

A diferencia de las páginas, la API no usa la sesión del navegador: quien la llama
inicia sesión en POST /api/login y manda el token en cada petición. Por eso no lleva
token CSRF.
"""
from flask import Blueprint

from app.extensions import csrf

bp = Blueprint("api", __name__, url_prefix="/api")
csrf.exempt(bp)


@bp.record_once
def _json_legible(estado):
    """Las respuestas JSON llevan las tildes tal cual ("Andrés" y no "Andr\u00e9s") y las
    llaves en el orden del formato acordado, no en orden alfabético."""
    estado.app.json.ensure_ascii = False
    estado.app.json.sort_keys = False


# Va al final para evitar la importación circular: routes.py importa bp de aquí.
from app.api import routes  # noqa: E402,F401
