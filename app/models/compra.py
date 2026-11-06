"""Tablas de compras a proveedores: proveedor, compra y detalle_compra (US-09).

Nombres, longitudes y restricciones tal como están en docs/diagramas/repuauto_bd.dbml.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Proveedor(db.Model):
    """Empresa a la que el almacén le compra repuestos. El NIT no se repite."""

    __tablename__ = "proveedor"

    id_proveedor: Mapped[int] = mapped_column(primary_key=True)
    nit: Mapped[str] = mapped_column(db.String(20), unique=True)
    nombre: Mapped[str] = mapped_column(db.String(100))
    telefono: Mapped[str | None] = mapped_column(db.String(20))
    correo: Mapped[str | None] = mapped_column(db.String(120))

    compras: Mapped[list["Compra"]] = relationship(back_populates="proveedor")

    def __repr__(self):
        return f"<Proveedor {self.nit}>"


class Compra(db.Model):
    """Una compra a un proveedor, registrada por un administrador.

    Versión mínima (D2): al registrarla, las cantidades se suman al stock. total es la
    suma de los detalles.
    """

    __tablename__ = "compra"
    __table_args__ = (CheckConstraint("total >= 0", name="chk_compra_total"),)

    id_compra: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[datetime] = mapped_column(server_default=func.now())
    id_proveedor: Mapped[int] = mapped_column(ForeignKey("proveedor.id_proveedor"))
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    proveedor: Mapped["Proveedor"] = relationship(back_populates="compras")
    usuario: Mapped["Usuario"] = relationship()
    detalles: Mapped[list["DetalleCompra"]] = relationship(
        back_populates="compra", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Compra {self.id_compra}>"


class DetalleCompra(db.Model):
    """Un repuesto dentro de una compra, con lo que costó cada unidad.

    Un repuesto aparece una sola vez por compra: si llegan más, sube la cantidad.
    """

    __tablename__ = "detalle_compra"
    __table_args__ = (
        UniqueConstraint("id_compra", "id_repuesto"),
        CheckConstraint("cantidad > 0", name="chk_detalle_compra_cantidad"),
        CheckConstraint("costo_unitario >= 0", name="chk_detalle_compra_costo"),
    )

    id_detalle_compra: Mapped[int] = mapped_column(primary_key=True)
    id_compra: Mapped[int] = mapped_column(ForeignKey("compra.id_compra"))
    id_repuesto: Mapped[int] = mapped_column(ForeignKey("repuesto.id_repuesto"))
    cantidad: Mapped[int]
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    compra: Mapped["Compra"] = relationship(back_populates="detalles")
    repuesto: Mapped["Repuesto"] = relationship()

    @property
    def subtotal(self):
        return self.cantidad * self.costo_unitario

    def __repr__(self):
        return f"<DetalleCompra compra={self.id_compra} repuesto={self.id_repuesto}>"
