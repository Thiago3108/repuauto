"""Tabla de clientes (US-02).

Nombres, longitudes y valores por defecto tal como están en docs/diagramas/repuauto_bd.dbml.
"""
from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Cliente(db.Model):
    """La persona que compra, separada de su cuenta.

    id_usuario es NULL para el cliente de mostrador sin cuenta. Un vendedor enlaza la
    cuenta verificando la cédula en persona (US-02 T4), y una cuenta se enlaza a un
    solo cliente.
    """

    __tablename__ = "cliente"

    id_cliente: Mapped[int] = mapped_column(primary_key=True)
    cedula: Mapped[str] = mapped_column(db.String(20), unique=True)
    nombres: Mapped[str] = mapped_column(db.String(60))
    apellidos: Mapped[str] = mapped_column(db.String(60))
    telefono: Mapped[str | None] = mapped_column(db.String(20))
    id_usuario: Mapped[int | None] = mapped_column(ForeignKey("usuario.id_usuario"), unique=True)
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now())

    usuario: Mapped["Usuario | None"] = relationship(back_populates="cliente")

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"

    def __repr__(self):
        return f"<Cliente {self.cedula}>"
