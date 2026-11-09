"""Controlador del módulo Reportes (US-07).

Las rutas reciben la petición, llaman a services.py y eligen la plantilla.
No consultan la base de datos directamente: eso es trabajo de services.py.

UI-12 Reportes tiene tres informes con el mismo rango de fechas, cada uno en su pestaña:
- Consolidado (/reportes/): los totales del periodo y del inventario de hoy.
- Tabular (/reportes/tabular): el detalle en tablas, mes por mes, por proveedor, por
  cliente y por categoría.
- Gráfico (/reportes/grafico): los mismos datos en gráficos.
"""
from flask import render_template, request

from app.auth.decoradores import rol_requerido
from app.reportes import bp, services

INFORMES = (
    ("reportes.index", "Consolidado"),
    ("reportes.tabular", "Tabular"),
    ("reportes.grafico", "Gráfico"),
)


@bp.get("/")
@rol_requerido("administrador")
def index():
    """Informe consolidado: total vendido, comprado, clientes nuevos e inventario."""
    return render_template("reportes/consolidado.html", **_datos())


@bp.get("/tabular")
@rol_requerido("administrador")
def tabular():
    """Informe tabular: ventas y compras por mes, proveedores, clientes e inventario."""
    return render_template("reportes/tabular.html", **_datos())


@bp.get("/grafico")
@rol_requerido("administrador")
def grafico():
    """Informe gráfico: ventas y compras por mes, proveedores, clientes e inventario."""
    return render_template("reportes/grafico.html", **_datos())


def _datos():
    """Los reportes del rango de ?desde=&hasta=. Si las fechas no sirven, el mes actual
    y el aviso en error."""
    error = None
    try:
        inicio, fin = services.rango_de_fechas(
            request.args.get("desde", "").strip(), request.args.get("hasta", "").strip()
        )
    except services.RangoInvalido as rango:
        error = rango.mensaje
        inicio, fin = services.rango_de_fechas("", "")
    ventas = services.reporte_ventas(inicio, fin)
    compras = services.reporte_compras(inicio, fin)
    return {
        "informes": INFORMES,
        "ventas": ventas,
        "compras": compras,
        "consolidado": services.reporte_consolidado(ventas, compras),
        "clientes": services.reporte_clientes(inicio, fin),
        "inventario": services.reporte_inventario(),
        "error": error,
    }
