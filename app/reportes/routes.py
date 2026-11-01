"""Controlador del módulo Reportes (US-07).

Las rutas reciben la petición, llaman a services.py y eligen la plantilla.
No consultan la base de datos directamente: eso es trabajo de services.py.
"""
from flask import render_template, request

from app.auth.decoradores import rol_requerido
from app.reportes import bp, services


@bp.get("/")
@rol_requerido("administrador")
def index():
    """UI-12 Reportes. Por ahora el de ventas (T1); T2 y T3 agregan inventario y clientes."""
    desde = request.args.get("desde", "").strip()
    hasta = request.args.get("hasta", "").strip()
    error = None
    try:
        inicio, fin = services.rango_de_fechas(desde, hasta)
    except services.RangoInvalido as rango:
        error = rango.mensaje
        inicio, fin = services.rango_de_fechas("", "")
    return render_template(
        "reportes/index.html",
        ventas=services.reporte_ventas(inicio, fin),
        error=error,
    )
