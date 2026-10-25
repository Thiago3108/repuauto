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


def listar_ventas(limite=50):
    """Las ventas más recientes primero."""
    return db.session.scalars(
        db.select(Venta).order_by(Venta.fecha.desc(), Venta.id_venta.desc()).limit(limite)
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
