"""Tablas de vehículos: marca_vehiculo, vehiculo y repuesto_vehiculo (US-03).

Nombres, longitudes y restricciones tal como están en docs/diagramas/repuauto_bd.dbml.
"""
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from app.extensions import db


class MarcaVehiculo(db.Model):
    """Fabricante del carro (Toyota, Chevrolet...). Va aparte de marca_repuesto."""

    __tablename__ = "marca_vehiculo"

    id_marca_vehiculo: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(db.String(60), unique=True)

    vehiculos: Mapped[list["Vehiculo"]] = relationship(back_populates="marca")

    def __repr__(self):
        return f"<MarcaVehiculo {self.nombre}>"


class Vehiculo(db.Model):
    """Un vehículo del catálogo: marca, línea, referencia opcional y año.

    El año es el "modelo" que aparece en la licencia de tránsito.
    """

    __tablename__ = "vehiculo"

    id_vehiculo: Mapped[int] = mapped_column(primary_key=True)
    id_marca_vehiculo: Mapped[int] = mapped_column(ForeignKey("marca_vehiculo.id_marca_vehiculo"))
    linea: Mapped[str] = mapped_column(db.String(60))
    referencia: Mapped[str | None] = mapped_column(db.String(60))
    anio: Mapped[int]

    marca: Mapped[MarcaVehiculo] = relationship(back_populates="vehiculos")
    repuestos: Mapped[list["Repuesto"]] = relationship(
        secondary="repuesto_vehiculo",
        passive_deletes=True,
        order_by="Repuesto.nombre",
        backref=backref("vehiculos", passive_deletes=True),
    )

    @property
    def descripcion(self):
        """Ej.: Toyota Corolla XEi 1.8 2018."""
        partes = [self.marca.nombre, self.linea, self.referencia, str(self.anio)]
        return " ".join(parte for parte in partes if parte)

    def __repr__(self):
        return f"<Vehiculo {self.id_vehiculo} {self.linea} {self.anio}>"


class RepuestoVehiculo(db.Model):
    """Compatibilidad: qué repuestos le sirven a qué vehículo (US-03 T3 y US-05).

    La llave primaria compuesta (id_repuesto, id_vehiculo) impide duplicar una
    compatibilidad. Al eliminar un vehículo o un repuesto, sus filas se borran en cascada.
    """

    __tablename__ = "repuesto_vehiculo"

    id_repuesto: Mapped[int] = mapped_column(
        ForeignKey("repuesto.id_repuesto", ondelete="CASCADE"), primary_key=True
    )
    id_vehiculo: Mapped[int] = mapped_column(
        ForeignKey("vehiculo.id_vehiculo", ondelete="CASCADE"), primary_key=True
    )

    def __repr__(self):
        return f"<RepuestoVehiculo repuesto={self.id_repuesto} vehiculo={self.id_vehiculo}>"
