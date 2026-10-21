
"""Modelos de repuestos e inventario (US-04).

Las categorías y marcas de repuesto son independientes de las marcas
de vehículos. Los repuestos se desactivan en lugar de borrarse.
"""

from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Categoria(db.Model):
    """Categoría a la que pertenece un repuesto."""

    __tablename__ = "categoria"

    id_categoria: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(db.String(60), unique=True)

    repuestos: Mapped[list["Repuesto"]] = relationship(
        back_populates="categoria"
    )

    def __repr__(self):
        return f"<Categoria {self.nombre}>"


class MarcaRepuesto(db.Model):
    """Fabricante o marca comercial de un repuesto."""

    __tablename__ = "marca_repuesto"

    id_marca_repuesto: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(db.String(60), unique=True)

    repuestos: Mapped[list["Repuesto"]] = relationship(
        back_populates="marca"
    )

    def __repr__(self):
        return f"<MarcaRepuesto {self.nombre}>"


class Repuesto(db.Model):
    """Repuesto con precio, existencias y datos de clasificación."""

    __tablename__ = "repuesto"
    __table_args__ = (
        CheckConstraint(
            "precio_venta >= 0",
            name="chk_repuesto_precio",
        ),
        CheckConstraint(
            "stock_actual >= 0",
            name="chk_repuesto_stock",
        ),
        CheckConstraint(
            "stock_minimo >= 0",
            name="chk_repuesto_stock_minimo",
        ),
    )

    id_repuesto: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(db.String(30), unique=True)
    nombre: Mapped[str] = mapped_column(db.String(100))
    descripcion: Mapped[str | None] = mapped_column(Text)
    precio_venta: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    stock_actual: Mapped[int] = mapped_column(
        server_default=text("0")
    )
    stock_minimo: Mapped[int] = mapped_column(
        server_default=text("0")
    )
    id_categoria: Mapped[int] = mapped_column(
        ForeignKey("categoria.id_categoria")
    )
    id_marca_repuesto: Mapped[int] = mapped_column(
        ForeignKey("marca_repuesto.id_marca_repuesto")
    )
    activo: Mapped[bool] = mapped_column(
        server_default=text("true")
    )

    categoria: Mapped["Categoria"] = relationship(
        back_populates="repuestos"
    )
    marca: Mapped["MarcaRepuesto"] = relationship(
        back_populates="repuestos"
    )

    def __repr__(self):
        return f"<Repuesto {self.codigo}: {self.nombre}>"
