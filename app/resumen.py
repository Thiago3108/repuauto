"""Resumen de la página de inicio: las cifras del día que le sirven a cada rol.

Cada tarjeta trae titulo, valor, detalle, icono (Bootstrap Icons), color y el enlace a
donde se ve el detalle. Las cuentas son las mismas de los módulos: solo cuentan las
ventas Completadas, y un repuesto está por reponer si está agotado o bajo el mínimo.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

from flask import url_for
from sqlalchemy import func, or_

from app.extensions import db
from app.models import EstadoVenta, Repuesto, Venta


def resumen_para(usuario, hoy=None):
    """Las tarjetas de inicio del usuario, según su rol."""
    hoy = hoy or date.today()
    if usuario.tiene_rol("cliente"):
        return _de_cliente(usuario)
    tarjetas = [_ventas_de_hoy(hoy), _ventas_pendientes(), _por_reponer()]
    if usuario.tiene_rol("administrador"):
        tarjetas.append(_vendido_en_el_mes(hoy))
    return tarjetas


def _ventas(estado, desde=None, hasta=None, id_cliente=None):
    """(cantidad, total) de las ventas con ese estado."""
    consulta = (
        db.select(func.count(Venta.id_venta), func.coalesce(func.sum(Venta.total), 0))
        .join(Venta.estado)
        .filter(EstadoVenta.nombre == estado)
    )
    if desde:
        consulta = consulta.filter(Venta.fecha >= datetime.combine(desde, datetime.min.time()))
    if hasta:
        consulta = consulta.filter(Venta.fecha < datetime.combine(hasta + timedelta(days=1), datetime.min.time()))
    if id_cliente:
        consulta = consulta.filter(Venta.id_cliente == id_cliente)
    cantidad, total = db.session.execute(consulta).one()
    return cantidad, Decimal(total)


def _pesos(valor):
    return f"${valor:,.0f}"


def _plural(cantidad, singular, plural):
    return f"{cantidad} {singular if cantidad == 1 else plural}"


def _ventas_de_hoy(hoy):
    cantidad, total = _ventas("Completada", hoy, hoy)
    return {
        "titulo": "Ventas de hoy", "valor": _pesos(total),
        "detalle": _plural(cantidad, "venta completada", "ventas completadas"),
        "icono": "cash-coin", "color": "verde", "enlace": url_for("ventas.index", estado="Completada"),
    }


def _ventas_pendientes():
    cantidad, total = _ventas("Pendiente")
    return {
        "titulo": "Ventas pendientes", "valor": str(cantidad),
        "detalle": f"{_pesos(total)} por entregar" if cantidad else "Todo entregado",
        "icono": "hourglass-split", "color": "ambar", "enlace": url_for("ventas.index", estado="Pendiente"),
    }


def _por_reponer():
    agotados, bajos = db.session.execute(
        db.select(
            func.count().filter(Repuesto.stock_actual == 0),
            func.count().filter(Repuesto.stock_actual > 0, Repuesto.stock_actual < Repuesto.stock_minimo),
        ).filter(
            Repuesto.activo.is_(True),
            or_(Repuesto.stock_actual == 0, Repuesto.stock_actual < Repuesto.stock_minimo),
        )
    ).one()
    return {
        "titulo": "Repuestos por reponer", "valor": str(agotados + bajos),
        "detalle": f"{_plural(agotados, 'agotado', 'agotados')} · {bajos} con stock bajo" if agotados + bajos else "Inventario al día",
        "icono": "exclamation-triangle", "color": "rojo" if agotados else "ambar", "enlace": url_for("repuestos.stock"),
    }


def _vendido_en_el_mes(hoy):
    cantidad, total = _ventas("Completada", hoy.replace(day=1), hoy)
    return {
        "titulo": "Vendido este mes", "valor": _pesos(total),
        "detalle": _plural(cantidad, "venta", "ventas"),
        "icono": "graph-up-arrow", "color": "azul", "enlace": url_for("reportes.index"),
    }


def _de_cliente(usuario):
    if usuario.cliente is None:
        return []
    id_cliente = usuario.cliente.id_cliente
    compras, total = _ventas("Completada", id_cliente=id_cliente)
    pendientes, _ = _ventas("Pendiente", id_cliente=id_cliente)
    return [
        {
            "titulo": "Mis compras", "valor": str(compras), "detalle": f"{_pesos(total)} en total",
            "icono": "bag-check", "color": "azul", "enlace": url_for("ventas.mis_compras"),
        },
        {
            "titulo": "Por recoger", "valor": str(pendientes),
            "detalle": "Repuestos apartados a tu nombre" if pendientes else "No tienes compras pendientes",
            "icono": "hourglass-split", "color": "ambar", "enlace": url_for("ventas.mis_compras", estado="Pendiente"),
        },
    ]
