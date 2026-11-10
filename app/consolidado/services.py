"""Informe consolidado de las dos sedes: junta las facturas, filtra y suma.

Las rutas llaman a estas funciones y las plantillas nunca tocan la base de datos ni la
otra sede.
"""
import unicodedata
from decimal import Decimal

from flask import current_app

from app.api import services as api
from app.consolidado import sedes

TIPOS = api.TIPOS
CAMPOS = ("subtotal", "iva", "total")


def informe(desde, hasta, tipo=None, sucursal=None, tercero=None):
    """Facturas de las dos sedes entre dos fechas, con filtros y totales.

    - tipo: "venta", "compra" o None para las dos.
    - sucursal: el nombre de una sede o None para las dos.
    - tercero: texto que se busca en el documento o el nombre, sin importar tildes ni
      mayúsculas.

    Si la otra sede no responde, el informe trae solo esta sede y aviso explica por qué.

    Devuelve un diccionario con sucursales (nombres), aviso, facturas (cada una con su
    sucursal, de la más reciente a la más antigua), por_sucursal (totales de cada sede
    por tipo) y totales (de todo lo filtrado, por tipo).
    """
    local = current_app.config["API_SUCURSAL"]
    remota = sedes.nombre_remota()
    facturas = [dict(f, sucursal=local) for f in api.facturas(desde, hasta)["facturas"]]
    aviso = None
    try:
        facturas += [dict(f, sucursal=remota) for f in sedes.facturas_remotas(desde, hasta)]
    except sedes.SedeNoDisponible as falla:
        aviso = falla.mensaje

    facturas = [f for f in facturas if _pasa(f, tipo, sucursal, tercero)]
    facturas.sort(key=lambda f: (f["fecha"], f["sucursal"], f["numero"]), reverse=True)

    nombres = [local, remota]
    return {
        "sucursales": nombres,
        "aviso": aviso,
        "facturas": facturas,
        "por_sucursal": [
            {"sucursal": nombre, **_totales([f for f in facturas if f["sucursal"] == nombre])}
            for nombre in nombres
            if sucursal in (None, nombre)
        ],
        "totales": _totales(facturas),
    }


def _pasa(factura, tipo, sucursal, tercero):
    if tipo and factura["tipo"] != tipo:
        return False
    if sucursal and factura["sucursal"] != sucursal:
        return False
    if tercero:
        texto = _normal(f"{factura['tercero']['documento']} {factura['tercero']['nombre']}")
        return all(palabra in texto for palabra in _normal(tercero).split())
    return True


def _totales(facturas):
    """Para cada tipo: cantidad y sumas de subtotal, IVA y total. Más la diferencia de
    lo vendido menos lo comprado."""
    totales = {}
    for tipo in TIPOS:
        del_tipo = [f for f in facturas if f["tipo"] == tipo]
        totales[tipo] = {"cantidad": len(del_tipo)} | {
            campo: sum((Decimal(f[campo]) for f in del_tipo), Decimal("0")) for campo in CAMPOS
        }
    totales["diferencia"] = totales["venta"]["total"] - totales["compra"]["total"]
    return totales


def _normal(texto):
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sin_tildes.lower()
