"""Tablas de ventas: estado_venta, venta y detalle_venta (US-06 y US-08).

Nombres, longitudes y restricciones tal como están en docs/diagramas/repuauto_bd.dbml.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db

METODOS_DE_PAGO = ("Efectivo", "Tarjeta", "Transferencia")
ESTADOS_DE_VENTA = ("Pendiente", "Completada", "Cancelada")


class EstadoVenta(db.Model):
    """Pendiente, Completada o Cancelada. Se carga con flask seed.

    El stock se descuenta al registrar la venta (el repuesto queda apartado) y se
    devuelve si la venta se cancela.
    """

    __tablename__ = "estado_venta"

    id_estado_venta: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(db.String(30), unique=True)

    ventas: Mapped[list["Venta"]] = relationship(back_populates="estado")

    def __repr__(self):
        return f"<EstadoVenta {self.nombre}>"


class Venta(db.Model):
    """Una venta a un cliente, registrada por un vendedor o un administrador.

    total es la suma de los detalles. Se guarda para que los reportes (US-07) no tengan
    que sumarlos cada vez.
    """

    __tablename__ = "venta"
    __table_args__ = (
        CheckConstraint(
            "metodo_pago in ('Efectivo', 'Tarjeta', 'Transferencia')", name="chk_venta_metodo_pago"
        ),
        CheckConstraint("total >= 0", name="chk_venta_total"),
    )

    id_venta: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[datetime] = mapped_column(server_default=func.now())
    id_cliente: Mapped[int] = mapped_column(ForeignKey("cliente.id_cliente"))
    id_vendedor: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"))
    id_estado_venta: Mapped[int] = mapped_column(ForeignKey("estado_venta.id_estado_venta"))
    metodo_pago: Mapped[str] = mapped_column(db.String(30))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    cliente: Mapped["Cliente"] = relationship()
    vendedor: Mapped["Usuario"] = relationship()
    estado: Mapped["EstadoVenta"] = relationship(back_populates="ventas")
    detalles: Mapped[list["DetalleVenta"]] = relationship(
        back_populates="venta", cascade="all, delete-orphan"
    )

    @property
    def codigo(self):
        """Código legible de la venta para mostrar al cliente (US-08)."""
        return f"#VTA-{self.id_venta:04d}"

    @property
    def cantidad_productos(self):
        """Total de unidades compradas en la venta."""
        return sum(detalle.cantidad for detalle in self.detalles)

    def __repr__(self):
        return f"<Venta {self.id_venta}>"


class DetalleVenta(db.Model):
    """Un repuesto dentro de una venta.

    precio_unitario se copia de repuesto.precio_venta al vender, para que el histórico no
    cambie si después sube el precio. Un repuesto aparece una sola vez por venta: si
    llevan más, sube la cantidad.
    """

    __tablename__ = "detalle_venta"
    __table_args__ = (
        UniqueConstraint("id_venta", "id_repuesto"),
        CheckConstraint("cantidad > 0", name="chk_detalle_venta_cantidad"),
        CheckConstraint("precio_unitario >= 0", name="chk_detalle_venta_precio"),
    )

    id_detalle_venta: Mapped[int] = mapped_column(primary_key=True)
    id_venta: Mapped[int] = mapped_column(ForeignKey("venta.id_venta"))
    id_repuesto: Mapped[int] = mapped_column(ForeignKey("repuesto.id_repuesto"))
    cantidad: Mapped[int]
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    venta: Mapped["Venta"] = relationship(back_populates="detalles")
    repuesto: Mapped["Repuesto"] = relationship()

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __repr__(self):
        return f"<DetalleVenta venta={self.id_venta} repuesto={self.id_repuesto}>"
