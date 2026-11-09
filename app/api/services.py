"""Lógica de la API REST: tokens de acceso y facturas en el formato acordado entre sedes.

Las rutas llaman a estas funciones; aquí no se arma ninguna respuesta HTTP.
"""
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.extensions import db
from app.models import Compra, EstadoVenta, Usuario, Venta
from app.reportes.services import _en_rango

TIPOS = ("venta", "compra")
# Colombia no cambia la hora en el año: siempre UTC-5.
HORA_COLOMBIA = timezone(timedelta(hours=-5), "COT")
CENTAVO = Decimal("0.01")


# ---------- Tokens de acceso ----------


class TokenInvalido(Exception):
    """El token no sirve. mensaje explica por qué."""

    def __init__(self, mensaje):
        super().__init__(mensaje)
        self.mensaje = mensaje


def _firmador():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="api-token")


def crear_token(usuario):
    """Token firmado con el id del usuario. Vence a las API_TOKEN_HORAS horas."""
    return _firmador().dumps({"id": usuario.id_usuario})


def duracion_token():
    """Segundos que dura un token."""
    return int(current_app.config["API_TOKEN_HORAS"] * 3600)


def usuario_del_token(token):
    """Devuelve el usuario dueño del token. Lanza TokenInvalido si el token está mal
    escrito, fue alterado, ya venció o la cuenta fue desactivada."""
    try:
        datos = _firmador().loads(token, max_age=duracion_token())
    except SignatureExpired:
        raise TokenInvalido("El token venció. Inicia sesión otra vez en POST /api/login.")
    except BadSignature:
        raise TokenInvalido("El token no es válido.")
    usuario = db.session.get(Usuario, datos.get("id"))
    if usuario is None or not usuario.activo:
        raise TokenInvalido("La cuenta del token ya no está activa.")
    return usuario


# ---------- Facturas ----------


def facturas(desde, hasta, tipo=None):
    """Facturas de venta y de compra entre dos fechas, en el formato acordado entre sedes.

    - Ventas: solo las Completadas. Las Pendientes no se han pagado y las Canceladas
      devolvieron el stock.
    - Compras: todas, porque suman al stock apenas se registran.
    - El IVA va incluido en el total: subtotal = total / (1 + API_IVA %).
    - tipo puede ser "venta", "compra" o None para las dos.

    Devuelve el diccionario listo para convertir en JSON, con las facturas de la más
    antigua a la más reciente y un resumen por tipo.
    """
    lista = []
    if tipo in (None, "venta"):
        ventas = db.session.scalars(
            db.select(Venta)
            .join(Venta.estado)
            .filter(EstadoVenta.nombre == "Completada", *_en_rango(Venta.fecha, desde, hasta))
            .order_by(Venta.fecha, Venta.id_venta)
        )
        lista += [_factura_de_venta(venta) for venta in ventas]
    if tipo in (None, "compra"):
        compras = db.session.scalars(
            db.select(Compra)
            .filter(*_en_rango(Compra.fecha, desde, hasta))
            .order_by(Compra.fecha, Compra.id_compra)
        )
        lista += [_factura_de_compra(compra) for compra in compras]
    lista.sort(key=lambda factura: (factura["fecha"], factura["numero"]))

    return {
        "sucursal": current_app.config["API_SUCURSAL"],
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "moneda": "COP",
        "iva_porcentaje": current_app.config["API_IVA"],
        "resumen": {t: _resumen(lista, t) for t in TIPOS if tipo in (None, t)},
        "facturas": lista,
    }


def numero_de_venta(id_venta):
    return f"V-{id_venta:06d}"


def numero_de_compra(id_compra):
    return f"C-{id_compra:06d}"


def _factura_de_venta(venta):
    cliente = venta.cliente
    return _factura(
        "venta", numero_de_venta(venta.id_venta), venta.fecha,
        cliente.cedula, cliente.nombre_completo, venta.total,
    )


def _factura_de_compra(compra):
    proveedor = compra.proveedor
    return _factura(
        "compra", numero_de_compra(compra.id_compra), compra.fecha,
        proveedor.nit, proveedor.nombre, compra.total,
    )


def _factura(tipo, numero, fecha, documento, nombre, total):
    subtotal, iva = separar_iva(total)
    return {
        "tipo": tipo,
        "numero": numero,
        "fecha": fecha_iso(fecha),
        "tercero": {"documento": documento, "nombre": nombre},
        "subtotal": _texto(subtotal),
        "iva": _texto(iva),
        "total": _texto(total),
    }


def separar_iva(total):
    """(subtotal, iva) de un total que ya trae el IVA incluido. Los dos suman el total."""
    total = Decimal(total).quantize(CENTAVO)
    porcentaje = Decimal(str(current_app.config["API_IVA"]))
    subtotal = (total / (1 + porcentaje / 100)).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    return subtotal, total - subtotal


def fecha_iso(fecha):
    """Fecha y hora con la zona de Colombia, por ejemplo 2026-10-30T10:15:00-05:00.

    La base guarda la hora local sin zona; si ya trae zona, se pasa a la de Colombia.
    """
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=HORA_COLOMBIA)
    return fecha.astimezone(HORA_COLOMBIA).isoformat(timespec="seconds")


def _resumen(lista, tipo):
    del_tipo = [f for f in lista if f["tipo"] == tipo]
    sumar = lambda campo: _texto(sum((Decimal(f[campo]) for f in del_tipo), Decimal("0")))  # noqa: E731
    return {"cantidad": len(del_tipo), "subtotal": sumar("subtotal"), "iva": sumar("iva"), "total": sumar("total")}


def _texto(valor):
    """El dinero va como texto con 2 decimales, para no perder centavos con decimales binarios."""
    return str(Decimal(valor).quantize(CENTAVO))
