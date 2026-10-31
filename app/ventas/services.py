"""Lógica de negocio del módulo Ventas (US-06 y US-08).

Aquí van las reglas del negocio: validar, consultar y guardar usando los modelos.
Las rutas llaman a estas funciones y las plantillas nunca tocan la base de datos.
"""
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from app.clientes.services import buscar_por_cedula
from app.extensions import db
from app.models import DetalleVenta, EstadoVenta, Repuesto, Venta
from app.models.venta import METODOS_DE_PAGO


class VentaRechazada(Exception):
    """No se puede guardar la venta. faltantes son los repuestos sin stock suficiente."""

    def __init__(self, mensaje, faltantes=()):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.faltantes = list(faltantes)


def buscar_cliente(cedula):
    return buscar_por_cedula(cedula.strip())


def repuestos_para_vender():
    """Los repuestos activos, para elegir en la venta. Muestran su precio y su stock."""
    return db.session.scalars(
        db.select(Repuesto).filter(Repuesto.activo.is_(True)).order_by(Repuesto.nombre)
    ).all()


def obtener_venta(id_venta):
    return db.session.get(Venta, id_venta)


def listar_ventas(estado=None, limite=50):
    """Las ventas más recientes primero. Con estado, solo las de ese estado (UI-07)."""
    consulta = db.select(Venta)
    if estado:
        consulta = consulta.join(Venta.estado).filter(EstadoVenta.nombre == estado)
    return db.session.scalars(
        consulta.order_by(Venta.fecha.desc(), Venta.id_venta.desc()).limit(limite)
    ).all()


def registrar_venta(cliente, vendedor, lineas, metodo_pago, completada=True):
    """Guarda una venta y descuenta el stock en una sola transacción (US-06 T2 y T3).

    lineas es una lista de (id_repuesto, cantidad). Si un repuesto se repite, se suman
    las cantidades, porque un repuesto aparece una sola vez por venta.

    - El precio unitario se copia del precio vigente del repuesto y el total se calcula.
    - Las filas de los repuestos se bloquean (SELECT ... FOR UPDATE) mientras se revisa
      el stock, para que dos ventas al mismo tiempo no vendan la misma unidad.
    - Si algún repuesto no tiene stock suficiente, no se guarda nada y faltantes dice cuáles.
    - Queda Completada si el cliente pagó y recibió el repuesto; si no, Pendiente. En los
      dos casos el stock se descuenta: el repuesto queda apartado.

    Devuelve la venta. Lanza VentaRechazada si no se puede guardar.
    """
    if cliente is None:
        raise VentaRechazada("Elige el cliente de la venta.")
    if metodo_pago not in METODOS_DE_PAGO:
        raise VentaRechazada("Elige el método de pago: Efectivo, Tarjeta o Transferencia.")

    cantidades = {}
    for id_repuesto, cantidad in lineas:
        if cantidad is None or cantidad <= 0:
            raise VentaRechazada("Cada repuesto debe llevar una cantidad mayor que 0.")
        cantidades[id_repuesto] = cantidades.get(id_repuesto, 0) + cantidad
    if not cantidades:
        raise VentaRechazada("Agrega al menos un repuesto a la venta.")

    try:
        repuestos = {
            repuesto.id_repuesto: repuesto
            for repuesto in db.session.scalars(
                db.select(Repuesto)
                .filter(Repuesto.id_repuesto.in_(cantidades))
                .order_by(Repuesto.id_repuesto)
                .with_for_update()
            )
        }
        if len(repuestos) < len(cantidades) or not all(r.activo for r in repuestos.values()):
            raise VentaRechazada("Uno de los repuestos ya no existe o está desactivado.")

        faltantes = [
            repuestos[id_repuesto]
            for id_repuesto, cantidad in cantidades.items()
            if repuestos[id_repuesto].stock_actual < cantidad
        ]
        if faltantes:
            detalle = ", ".join(f"{r.nombre} (quedan {r.stock_actual})" for r in faltantes)
            raise VentaRechazada(f"No hay stock suficiente de: {detalle}.", faltantes)

        estado = "Completada" if completada else "Pendiente"
        venta = Venta(
            cliente=cliente,
            vendedor=vendedor,
            estado=db.session.scalar(db.select(EstadoVenta).filter_by(nombre=estado)),
            metodo_pago=metodo_pago,
            total=Decimal("0"),
        )
        for id_repuesto, cantidad in cantidades.items():
            repuesto = repuestos[id_repuesto]
            venta.detalles.append(DetalleVenta(
                repuesto=repuesto, cantidad=cantidad, precio_unitario=repuesto.precio_venta,
            ))
            repuesto.stock_actual -= cantidad
        venta.total = sum((detalle.subtotal for detalle in venta.detalles), Decimal("0"))

        db.session.add(venta)
        db.session.commit()
    except VentaRechazada:
        db.session.rollback()
        raise
    except IntegrityError:
        db.session.rollback()
        raise VentaRechazada("No se pudo guardar la venta. Revisa los datos e inténtalo de nuevo.")
    return venta


def completar_venta(id_venta):
    """Una venta Pendiente pasa a Completada: el cliente pagó y se llevó el repuesto (US-06 T4).

    El stock no cambia, porque ya se descontó al registrar la venta.
    Devuelve la venta, o None si no existe. Lanza VentaRechazada si no está Pendiente.
    """
    venta = _venta_bloqueada(id_venta)
    if venta is None:
        return None
    if venta.estado.nombre != "Pendiente":
        db.session.rollback()
        raise VentaRechazada(f"Solo se completan las ventas pendientes. Esta está {venta.estado.nombre}.")
    venta.estado = _estado("Completada")
    db.session.commit()
    return venta


def cancelar_venta(id_venta):
    """Cancela una venta Pendiente o Completada y devuelve el stock (US-06 T4).

    Todo va en una sola transacción. La venta y sus repuestos se bloquean
    (SELECT ... FOR UPDATE), para que dos personas cancelando a la vez no devuelvan el
    stock dos veces. La venta no se borra: queda Cancelada y fuera de los reportes.

    Devuelve la venta, o None si no existe. Lanza VentaRechazada si ya estaba cancelada.
    """
    venta = _venta_bloqueada(id_venta)
    if venta is None:
        return None
    if venta.estado.nombre == "Cancelada":
        db.session.rollback()
        raise VentaRechazada("Esta venta ya estaba cancelada.")

    cantidades = {detalle.id_repuesto: detalle.cantidad for detalle in venta.detalles}
    repuestos = db.session.scalars(
        db.select(Repuesto)
        .filter(Repuesto.id_repuesto.in_(cantidades))
        .order_by(Repuesto.id_repuesto)
        .with_for_update()
    )
    for repuesto in repuestos:
        repuesto.stock_actual += cantidades[repuesto.id_repuesto]
    venta.estado = _estado("Cancelada")
    db.session.commit()
    return venta


def _venta_bloqueada(id_venta):
    """La venta leída de nuevo de la base y bloqueada hasta el commit o el rollback."""
    return db.session.get(Venta, id_venta, with_for_update=True, populate_existing=True)


def _estado(nombre):
    return db.session.scalar(db.select(EstadoVenta).filter_by(nombre=nombre))


# ---------- Estado e historial de compras del cliente (US-08) ----------


def extraer_id_venta(codigo_o_id):
    """Extrae el id_venta numérico desde un entero, un número o un código #VTA-0001."""
    if isinstance(codigo_o_id, int):
        return codigo_o_id if codigo_o_id > 0 else None
    texto = str(codigo_o_id or "").strip().upper()
    for prefijo in ("#VTA-", "VTA-", "#VTA", "VTA", "#"):
        if texto.startswith(prefijo):
            texto = texto[len(prefijo):]
            break
    if not texto.isdigit():
        return None
    id_venta = int(texto)
    return id_venta if id_venta > 0 else None


def listar_compras_cliente(usuario, estado=None):
    """Historial de compras del cliente que inició sesión, de la más reciente a la más
    antigua (US-08 T1 y T2). Si la cuenta no está enlazada a un cliente, devuelve []."""
    if usuario is None or usuario.cliente is None:
        return []
    consulta = db.select(Venta).filter(Venta.id_cliente == usuario.cliente.id_cliente)
    if estado:
        consulta = consulta.join(Venta.estado).filter(EstadoVenta.nombre == estado)
    return db.session.scalars(
        consulta.order_by(Venta.fecha.desc(), Venta.id_venta.desc())
    ).all()


def obtener_compra_cliente(usuario, codigo_o_id):
    """Devuelve la compra solo si pertenece al cliente que inició sesión (US-08 T1).

    Un cliente nunca puede ver compras de otro, aunque cambie el código en la URL.
    """
    if usuario is None or usuario.cliente is None:
        return None
    id_venta = extraer_id_venta(codigo_o_id)
    if id_venta is None:
        return None
    return db.session.scalar(
        db.select(Venta).filter(
            Venta.id_venta == id_venta,
            Venta.id_cliente == usuario.cliente.id_cliente,
        )
    )
