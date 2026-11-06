"""Lógica de negocio del módulo Proveedores y compras (US-09).

Aquí van las reglas del negocio: validar, consultar y guardar usando los modelos.
Las rutas llaman a estas funciones y las plantillas nunca tocan la base de datos.
"""
from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Compra, DetalleCompra, Proveedor, Repuesto

# ---------- Proveedores (US-09 T2) ----------


class NitRepetido(Exception):
    """El NIT ya es de otro proveedor. existente es ese proveedor, para poder mostrarlo."""

    def __init__(self, existente):
        super().__init__(f"El NIT {existente.nit} ya es de {existente.nombre}.")
        self.existente = existente


def listar_proveedores(busqueda=None):
    """Proveedores ordenados por nombre. Con busqueda, solo los que la tienen en el NIT o el nombre."""
    consulta = db.select(Proveedor)
    texto = (busqueda or "").strip()
    if texto:
        patron = "%" + texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        consulta = consulta.filter(or_(
            Proveedor.nit.ilike(patron, escape="\\"), Proveedor.nombre.ilike(patron, escape="\\"),
        ))
    return db.session.scalars(consulta.order_by(Proveedor.nombre, Proveedor.id_proveedor)).all()


def obtener_proveedor(id_proveedor):
    return db.session.get(Proveedor, id_proveedor)


def buscar_por_nit(nit):
    return db.session.scalar(db.select(Proveedor).filter_by(nit=nit))


def crear_proveedor(nit, nombre, telefono=None, correo=None):
    """Registra un proveedor. Lanza NitRepetido si el NIT ya existe."""
    existente = buscar_por_nit(nit)
    if existente is not None:
        raise NitRepetido(existente)

    proveedor = Proveedor(nit=nit, nombre=nombre, telefono=telefono or None, correo=correo or None)
    db.session.add(proveedor)
    _guardar_proveedor(nit)
    return proveedor


def actualizar_proveedor(proveedor, nit, nombre, telefono=None, correo=None):
    """Cambia los datos de un proveedor. Lanza NitRepetido si el NIT nuevo es de otro."""
    existente = buscar_por_nit(nit)
    if existente is not None and existente.id_proveedor != proveedor.id_proveedor:
        raise NitRepetido(existente)

    proveedor.nit = nit
    proveedor.nombre = nombre
    proveedor.telefono = telefono or None
    proveedor.correo = correo or None
    _guardar_proveedor(nit)
    return proveedor


def _guardar_proveedor(nit):
    try:
        db.session.commit()
    except IntegrityError:
        # Otra persona guardó el mismo NIT al mismo tiempo.
        db.session.rollback()
        raise NitRepetido(buscar_por_nit(nit))


# ---------- Compras (US-09 T3) ----------


class CompraRechazada(Exception):
    """No se puede guardar la compra. mensaje explica por qué."""

    def __init__(self, mensaje):
        super().__init__(mensaje)
        self.mensaje = mensaje


def repuestos_para_comprar():
    """Los repuestos activos, para elegir en la compra."""
    return db.session.scalars(
        db.select(Repuesto).filter(Repuesto.activo.is_(True)).order_by(Repuesto.nombre)
    ).all()


def listar_compras(limite=50):
    """Las compras más recientes primero."""
    return db.session.scalars(
        db.select(Compra).order_by(Compra.fecha.desc(), Compra.id_compra.desc()).limit(limite)
    ).all()


def obtener_compra(id_compra):
    return db.session.get(Compra, id_compra)


def registrar_compra(proveedor, usuario, lineas):
    """Guarda una compra y suma las cantidades al stock en una sola transacción (US-09 T3).

    lineas es una lista de (id_repuesto, cantidad, costo_unitario). Si un repuesto se
    repite con el mismo costo, se suman las cantidades; con costos distintos, se rechaza,
    porque un repuesto aparece una sola vez por compra.

    - Cada cantidad debe ser mayor que 0 y cada costo no puede ser negativo.
    - El total se calcula con los detalles.
    - Las filas de los repuestos se bloquean (SELECT ... FOR UPDATE) para que una venta al
      mismo tiempo no pise el stock nuevo.
    - Queda registrado el administrador que hizo la compra.

    Devuelve la compra. Lanza CompraRechazada si no se puede guardar; entonces no se guarda
    nada y el stock queda igual.
    """
    if proveedor is None:
        raise CompraRechazada("Elige el proveedor de la compra.")
    if usuario is None or not usuario.tiene_rol("administrador"):
        raise CompraRechazada("Solo un administrador puede registrar compras.")

    pedidos = {}
    for id_repuesto, cantidad, costo in lineas:
        if cantidad is None or cantidad <= 0:
            raise CompraRechazada("Cada repuesto debe llevar una cantidad mayor que 0.")
        if costo is None:
            raise CompraRechazada("Escribe el costo de cada repuesto.")
        if costo < 0:
            raise CompraRechazada("El costo de cada repuesto no puede ser negativo.")
        costo = Decimal(costo).quantize(Decimal("0.01"))
        if id_repuesto in pedidos:
            anterior, costo_anterior = pedidos[id_repuesto]
            if costo != costo_anterior:
                raise CompraRechazada("Un repuesto está dos veces con costos distintos. Déjalo en una sola línea.")
            cantidad += anterior
        pedidos[id_repuesto] = (cantidad, costo)
    if not pedidos:
        raise CompraRechazada("Agrega al menos un repuesto a la compra.")

    try:
        repuestos = {
            repuesto.id_repuesto: repuesto
            for repuesto in db.session.scalars(
                db.select(Repuesto)
                .filter(Repuesto.id_repuesto.in_(pedidos))
                .order_by(Repuesto.id_repuesto)
                .with_for_update()
            )
        }
        if len(repuestos) < len(pedidos) or not all(r.activo for r in repuestos.values()):
            raise CompraRechazada("Uno de los repuestos ya no existe o está desactivado.")

        compra = Compra(proveedor=proveedor, usuario=usuario, total=Decimal("0"))
        for id_repuesto, (cantidad, costo) in pedidos.items():
            repuesto = repuestos[id_repuesto]
            compra.detalles.append(DetalleCompra(repuesto=repuesto, cantidad=cantidad, costo_unitario=costo))
            repuesto.stock_actual += cantidad
        compra.total = sum((detalle.subtotal for detalle in compra.detalles), Decimal("0"))

        db.session.add(compra)
        db.session.commit()
    except CompraRechazada:
        db.session.rollback()
        raise
    except IntegrityError:
        db.session.rollback()
        raise CompraRechazada("No se pudo guardar la compra. Revisa los datos e inténtalo de nuevo.")
    return compra
