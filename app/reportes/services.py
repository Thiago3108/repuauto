"""Lógica de negocio del módulo Reportes (US-07).

Aquí van las reglas del negocio: validar, consultar y guardar usando los modelos.
Las rutas llaman a estas funciones y las plantillas nunca tocan la base de datos.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func

from app.extensions import db
from app.models import EstadoVenta, Venta

MESES = (
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
)


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
        .filter(
            EstadoVenta.nombre == "Completada",
            Venta.fecha >= datetime.combine(desde, datetime.min.time()),
            Venta.fecha < datetime.combine(hasta + timedelta(days=1), datetime.min.time()),
        )
        .group_by(mes)
    ).all()
    por_mes = {(fila.mes.year, fila.mes.month): (fila[1], Decimal(fila[2])) for fila in filas}

    meses = []
    anio, numero = desde.year, desde.month
    while (anio, numero) <= (hasta.year, hasta.month):
        ventas, total = por_mes.get((anio, numero), (0, Decimal("0")))
        meses.append({
            "anio": anio, "mes": numero, "nombre": f"{MESES[numero - 1]} {anio}",
            "ventas": ventas, "total": total,
        })
        anio, numero = (anio + 1, 1) if numero == 12 else (anio, numero + 1)

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
