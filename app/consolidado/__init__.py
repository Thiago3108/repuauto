"""Módulo Consolidado de sedes: junta las compras y ventas de RepuAuto con las de la
otra sede (grupo UD1) en un solo informe.

Las facturas de esta sede salen de la base de datos con el mismo formato de la API
(app/api). Las de la otra sede se piden por HTTP a su API y se traducen a ese formato
(sedes.py). Las rutas van bajo /consolidado y son solo para el administrador.
"""
from flask import Blueprint

bp = Blueprint("consolidado", __name__, url_prefix="/consolidado")

# Va al final para evitar la importación circular: routes.py importa bp de aquí.
from app.consolidado import routes  # noqa: E402,F401
