"""Lógica de negocio del módulo Reportes (US-07).

Aquí van las reglas del negocio: validar, consultar y guardar usando los modelos.
Las rutas llaman a estas funciones y las plantillas nunca tocan la base de datos.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import case, func, or_

from app.extensions import db
from app.models import Categoria, Cliente, Compra, EstadoVenta, Proveedor, Repuesto, Venta

MESES = (
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
)


ESTADOS_DE_STOCK = ("En stock", "Stock bajo", "Agotado")


class RangoInvalido(Exception):
    """Las fechas del reporte no sirven. mensaje explica por qué."""

    def __init__(self, mensaje):
        super().__init__(mensaje)
        self.mensaje = mensaje


def rango_de_fechas(desde, hasta, hoy=None):
    """Convierte las fechas del formulario (AAAA-MM-DD) en un rango (desde, hasta).

    Si falta desde, es el primer día del mes de hoy; si falta hasta, es hoy.
    Lanza RangoInvalido si una fecha no se entiende o si desde va después de hasta.
    """
    hoy = hoy or date.today()
    try:
        inicio = date.fromisoformat(desde) if desde else hoy.replace(day=1)
        fin = date.fromisoformat(hasta) if hasta else hoy
    except ValueError:
        raise RangoInvalido("Escribe las fechas con el formato AAAA-MM-DD.")
    if inicio > fin:
        raise RangoInvalido("La fecha inicial no puede ir después de la fecha final.")
    return inicio, fin


def reporte_ventas(desde, hasta):
    """Total vendido y número de ventas entre dos fechas, en total y por mes (US-07 T1).

    Solo cuentan las ventas Completadas: las Pendientes todavía no se pagan y las
    Canceladas devolvieron el stock. Las dos fechas se incluyen completas.

    Devuelve un diccionario con desde, hasta, total, ventas, promedio y meses. meses trae
    todos los meses del rango, también los que no tuvieron ventas, del más antiguo al más
    reciente; cada uno con anio, mes, nombre, total y ventas.
    """
    mes = func.date_trunc("month", Venta.fecha).label("mes")
    filas = db.session.execute(
        db.select(mes, func.count(Venta.id_venta), func.coalesce(func.sum(Venta.total), 0))
        .join(Venta.estado)
        .filter(EstadoVenta.nombre == "Completada", *_en_rango(Venta.fecha, desde, hasta))
        .group_by(mes)
    ).all()
    por_mes = {(fila.mes.year, fila.mes.month): (fila[1], Decimal(fila[2])) for fila in filas}

    meses = []
    for anio, numero, nombre in _meses(desde, hasta):
        ventas, total = por_mes.get((anio, numero), (0, Decimal("0")))
        meses.append({"anio": anio, "mes": numero, "nombre": nombre, "ventas": ventas, "total": total})

    ventas = sum(m["ventas"] for m in meses)
    total = sum((m["total"] for m in meses), Decimal("0"))
    return {
        "desde": desde,
        "hasta": hasta,
        "ventas": ventas,
        "total": total,
        "promedio": (total / ventas).quantize(Decimal("0.01")) if ventas else Decimal("0"),
        "meses": meses,
    }


def reporte_clientes(desde, hasta, limite=10):
    """Clientes nuevos y los que más compran entre dos fechas (US-07 T3).

    - Un cliente es nuevo en el mes en que se registró (cliente.creado_en), tenga cuenta
      o sea de mostrador.
    - Los que más compran se ordenan por lo que gastaron en ventas Completadas del rango;
      si empatan, por número de compras y luego por nombre. Se muestran los primeros
      limite.

    Devuelve un diccionario con desde, hasta, nuevos, meses y mejores. meses trae todos los
    meses del rango con anio, mes, nombre y nuevos. mejores trae cliente, compras y total.
    """
    mes = func.date_trunc("month", Cliente.creado_en).label("mes")
    filas = db.session.execute(
        db.select(mes, func.count(Cliente.id_cliente))
        .filter(*_en_rango(Cliente.creado_en, desde, hasta))
        .group_by(mes)
    ).all()
    por_mes = {(fila.mes.year, fila.mes.month): fila[1] for fila in filas}
    meses = [
        {"anio": anio, "mes": numero, "nombre": nombre, "nuevos": por_mes.get((anio, numero), 0)}
        for anio, numero, nombre in _meses(desde, hasta)
    ]

    total = func.sum(Venta.total).label("total")
    compras = func.count(Venta.id_venta).label("compras")
    mejores = db.session.execute(
        db.select(Cliente, compras, total)
        .join(Venta, Venta.id_cliente == Cliente.id_cliente)
        .join(Venta.estado)
        .filter(EstadoVenta.nombre == "Completada", *_en_rango(Venta.fecha, desde, hasta))
        .group_by(Cliente.id_cliente)
        .order_by(total.desc(), compras.desc(), Cliente.nombres, Cliente.apellidos)
        .limit(limite)
    ).all()

    return {
        "desde": desde,
        "hasta": hasta,
        "nuevos": sum(m["nuevos"] for m in meses),
        "meses": meses,
        "mejores": [
            {"cliente": fila.Cliente, "compras": fila.compras, "total": Decimal(fila.total)}
            for fila in mejores
        ],
    }


def reporte_compras(desde, hasta, limite=10):
    """Total comprado a proveedores entre dos fechas, por mes y por proveedor.

    Una compra suma al stock apenas se registra, así que todas cuentan. Las dos fechas
    se incluyen completas.

    Devuelve un diccionario con desde, hasta, compras, total, meses y proveedores. meses
    trae todos los meses del rango con anio, mes, nombre, compras y total. proveedores trae
    los primeros limite, de mayor a menor total, cada uno con proveedor, compras y total.
    """
    mes = func.date_trunc("month", Compra.fecha).label("mes")
    filas = db.session.execute(
        db.select(mes, func.count(Compra.id_compra), func.coalesce(func.sum(Compra.total), 0))
        .filter(*_en_rango(Compra.fecha, desde, hasta))
        .group_by(mes)
    ).all()
    por_mes = {(fila.mes.year, fila.mes.month): (fila[1], Decimal(fila[2])) for fila in filas}

    meses = []
    for anio, numero, nombre in _meses(desde, hasta):
        compras, total = por_mes.get((anio, numero), (0, Decimal("0")))
        meses.append({"anio": anio, "mes": numero, "nombre": nombre, "compras": compras, "total": total})

    total = func.sum(Compra.total).label("total")
    compras = func.count(Compra.id_compra).label("compras")
    proveedores = db.session.execute(
        db.select(Proveedor, compras, total)
        .join(Compra, Compra.id_proveedor == Proveedor.id_proveedor)
        .filter(*_en_rango(Compra.fecha, desde, hasta))
        .group_by(Proveedor.id_proveedor)
        .order_by(total.desc(), compras.desc(), Proveedor.nombre)
        .limit(limite)
    ).all()

    return {
        "desde": desde,
        "hasta": hasta,
        "compras": sum(m["compras"] for m in meses),
        "total": sum((m["total"] for m in meses), Decimal("0")),
        "meses": meses,
        "proveedores": [
            {"proveedor": fila.Proveedor, "compras": fila.compras, "total": Decimal(fila.total)}
            for fila in proveedores
        ],
    }


def reporte_consolidado(ventas, compras):
    """Junta el reporte de ventas y el de compras del mismo rango, mes por mes.

    diferencia es lo vendido menos lo comprado. No es la utilidad: lo comprado en un mes
    puede venderse en otro.

    Devuelve un diccionario con vendido, comprado, diferencia y meses (cada uno con nombre,
    vendido, comprado y diferencia).
    """
    meses = [
        {
            "nombre": venta["nombre"],
            "vendido": venta["total"],
            "comprado": compra["total"],
            "diferencia": venta["total"] - compra["total"],
        }
        for venta, compra in zip(ventas["meses"], compras["meses"], strict=True)
    ]
    return {
        "vendido": ventas["total"],
        "comprado": compras["total"],
        "diferencia": ventas["total"] - compras["total"],
        "meses": meses,
    }


def reporte_inventario():
    """Repuestos activos por categoría y estado del stock, como están hoy (US-07 T2).

    - Agotado: no queda ninguna unidad.
    - Stock bajo: quedan unidades, pero menos que el stock mínimo (como en UI-09).
    - En stock: el resto.

    No depende del rango de fechas: muestra el inventario de este momento. valor es
    lo que vale el stock a precio de venta.

    Devuelve un diccionario con repuestos, unidades, valor, estados (cuántos repuestos hay
    en cada estado), categorias (cada una con nombre, repuestos, unidades, valor y estados)
    y por_reponer (los repuestos agotados o con stock bajo, primero los que menos tienen).
    """
    estado = case(
        (Repuesto.stock_actual == 0, "Agotado"),
        (Repuesto.stock_actual < Repuesto.stock_minimo, "Stock bajo"),
        else_="En stock",
    ).label("estado")
    filas = db.session.execute(
        db.select(
            Categoria.nombre,
            estado,
            func.count(Repuesto.id_repuesto),
            func.sum(Repuesto.stock_actual),
            func.sum(Repuesto.stock_actual * Repuesto.precio_venta),
        )
        .join(Repuesto.categoria)
        .filter(Repuesto.activo.is_(True))
        .group_by(Categoria.nombre, estado)
        .order_by(Categoria.nombre)
    ).all()

    categorias = {}
    for nombre, estado_stock, repuestos, unidades, valor in filas:
        categoria = categorias.setdefault(nombre, {
            "nombre": nombre, "repuestos": 0, "unidades": 0, "valor": Decimal("0"),
            "estados": dict.fromkeys(ESTADOS_DE_STOCK, 0),
        })
        categoria["repuestos"] += repuestos
        categoria["unidades"] += unidades
        categoria["valor"] += Decimal(valor)
        categoria["estados"][estado_stock] += repuestos
    categorias = list(categorias.values())

    por_reponer = db.session.scalars(
        db.select(Repuesto)
        .filter(
            Repuesto.activo.is_(True),
            or_(Repuesto.stock_actual == 0, Repuesto.stock_actual < Repuesto.stock_minimo),
        )
        .order_by(Repuesto.stock_actual, Repuesto.nombre)
    ).all()
    return {
        "repuestos": sum(c["repuestos"] for c in categorias),
        "unidades": sum(c["unidades"] for c in categorias),
        "valor": sum((c["valor"] for c in categorias), Decimal("0")),
        "estados": {e: sum(c["estados"][e] for c in categorias) for e in ESTADOS_DE_STOCK},
        "categorias": categorias,
        "por_reponer": por_reponer,
    }


def _en_rango(columna, desde, hasta):
    """Filtros para que la columna caiga entre las dos fechas, incluidas completas."""
    return (
        columna >= datetime.combine(desde, datetime.min.time()),
        columna < datetime.combine(hasta + timedelta(days=1), datetime.min.time()),
    )


def _meses(desde, hasta):
    """(anio, mes, nombre) de cada mes del rango, del más antiguo al más reciente."""
    anio, numero = desde.year, desde.month
    while (anio, numero) <= (hasta.year, hasta.month):
        yield anio, numero, f"{MESES[numero - 1]} {anio}"
        anio, numero = (anio + 1, 1) if numero == 12 else (anio, numero + 1)
