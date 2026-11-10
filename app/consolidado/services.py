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


# ---------- Inventario de las dos sedes ----------

ESTADOS = api.ESTADOS
NOMBRES_DE_ESTADO = {"en_stock": "En stock", "stock_bajo": "Stock bajo", "agotado": "Agotado"}


def inventario(sucursal=None, estado=None, buscar=None):
    """Inventario de hoy de las dos sedes, con filtros y totales por sede.

    - sucursal: el nombre de una sede o None para las dos.
    - estado: "en_stock", "stock_bajo", "agotado" o None para todos.
    - buscar: texto que se busca en el código, el nombre, la categoría o la marca, sin
      importar tildes ni mayúsculas.

    Si la otra sede no responde o no publica su inventario, trae solo esta sede y aviso
    explica por qué.

    Devuelve un diccionario con sucursales, aviso, por_sucursal (el resumen de cada sede,
    sin filtrar), totales (la suma de esos resúmenes) y productos (filtrados, cada uno con
    su sucursal).
    """
    local = current_app.config["API_SUCURSAL"]
    remota = sedes.nombre_remota()
    datos_local = api.inventario()
    sedes_con_datos = [(local, datos_local["resumen"], datos_local["productos"])]
    aviso = None
    try:
        remoto = sedes.inventario_remoto()
        sedes_con_datos.append((remota, remoto["resumen"], remoto["productos"]))
    except sedes.SedeNoDisponible as falla:
        aviso = falla.mensaje

    por_sucursal = [
        {"sucursal": nombre, **_resumen_numerico(resumen)}
        for nombre, resumen, _ in sedes_con_datos
        if sucursal in (None, nombre)
    ]
    productos = [
        dict(producto, sucursal=nombre)
        for nombre, _, lista in sedes_con_datos
        for producto in lista
        if _producto_pasa(producto, nombre, sucursal, estado, buscar)
    ]
    campos = ("productos", "unidades", "valor", *ESTADOS)
    return {
        "sucursales": [local, remota],
        "aviso": aviso,
        "por_sucursal": por_sucursal,
        "totales": {campo: sum((fila[campo] for fila in por_sucursal), 0) for campo in campos},
        "productos": productos,
    }


def _resumen_numerico(resumen):
    return {
        "productos": int(resumen["productos"]),
        "unidades": int(resumen["unidades"]),
        "valor": Decimal(str(resumen["valor"])),
        **{estado: int(resumen.get(estado, 0)) for estado in ESTADOS},
    }


def _producto_pasa(producto, nombre_sede, sucursal, estado, buscar):
    if sucursal and nombre_sede != sucursal:
        return False
    if estado and producto["estado"] != estado:
        return False
    if buscar:
        texto = _normal(" ".join(str(producto.get(c, "")) for c in ("codigo", "nombre", "categoria", "marca")))
        return all(palabra in texto for palabra in _normal(buscar).split())
    return True
