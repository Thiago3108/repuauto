"""Controlador del módulo Consolidado de sedes.

La ruta recibe los filtros, llama a services.py y elige la plantilla.
"""
from flask import render_template, request

from app.auth.decoradores import rol_requerido
from app.consolidado import bp, services
from app.reportes.services import RangoInvalido, rango_de_fechas


@bp.get("/")
@rol_requerido("administrador")
def index():
    """Informe consolidado de compras y ventas de las dos sedes, con filtros."""
    error = None
    try:
        desde, hasta = rango_de_fechas(
            request.args.get("desde", "").strip(), request.args.get("hasta", "").strip()
        )
    except RangoInvalido as rango:
        error = rango.mensaje
        desde, hasta = rango_de_fechas("", "")
    tipo = request.args.get("tipo", "").strip() or None
    if tipo not in (None, *services.TIPOS):
        tipo = None
    sucursal = request.args.get("sucursal", "").strip() or None
    tercero = request.args.get("tercero", "").strip() or None

    datos = services.informe(desde, hasta, tipo=tipo, sucursal=sucursal, tercero=tercero)
    return render_template(
        "consolidado/index.html",
        datos=datos,
        filtros={"desde": desde, "hasta": hasta, "tipo": tipo, "sucursal": sucursal, "tercero": tercero or ""},
        error=error,
    )
