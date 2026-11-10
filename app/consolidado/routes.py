"""Controlador del módulo Consolidado de sedes.

Las rutas reciben los filtros, llaman a services.py y eligen la plantilla. Hay dos
pestañas: Facturas (/consolidado/) e Inventario (/consolidado/inventario).
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


@bp.get("/inventario")
@rol_requerido("administrador")
def inventario():
    """Inventario de hoy de las dos sedes, con filtros por sede, estado y texto."""
    estado = request.args.get("estado", "").strip() or None
    if estado not in (None, *services.ESTADOS):
        estado = None
    sucursal = request.args.get("sucursal", "").strip() or None
    buscar = request.args.get("buscar", "").strip() or None
    return render_template(
        "consolidado/inventario.html",
        datos=services.inventario(sucursal=sucursal, estado=estado, buscar=buscar),
        filtros={"estado": estado, "sucursal": sucursal, "buscar": buscar or ""},
        nombres_de_estado=services.NOMBRES_DE_ESTADO,
    )
