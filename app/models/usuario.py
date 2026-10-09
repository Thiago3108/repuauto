"""Tablas de cuentas: rol y usuario (US-01).

Nombres, longitudes y valores por defecto tal como están en docs/diagramas/repuauto_bd.dbml.
"""
from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import ForeignKey, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Rol(db.Model):
    """Rol de una cuenta: cliente, vendedor o administrador. Se carga con flask seed."""

    __tablename__ = "rol"

    id_rol: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(db.String(30), unique=True)

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="rol")

    def __repr__(self):
        return f"<Rol {self.nombre}>"


class Usuario(UserMixin, db.Model):
    """Cuenta para iniciar sesión, de cualquiera de los tres roles.

    Nunca guarda la contraseña: solo su hash. No se borra: se desactiva con activo = False,
    porque sus ventas siguen apuntando a él.

    UserMixin le da lo que Flask-Login necesita para manejar la sesión.
    """

    __tablename__ = "usuario"

    id_usuario: Mapped[int] = mapped_column(primary_key=True)
    correo: Mapped[str] = mapped_column(db.String(120), unique=True)
    contrasena_hash: Mapped[str] = mapped_column(db.String(255))
    nombre: Mapped[str] = mapped_column(db.String(100))
    id_rol: Mapped[int] = mapped_column(ForeignKey("rol.id_rol"))
    activo: Mapped[bool] = mapped_column(server_default=true())
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now())

    rol: Mapped[Rol] = relationship(back_populates="usuarios")
    cliente: Mapped["Cliente | None"] = relationship(back_populates="usuario")

    def get_id(self):
        """Lo que Flask-Login guarda en la cookie de sesión."""
        return str(self.id_usuario)

    @property
    def is_active(self):
        """Una cuenta desactivada no puede iniciar sesión."""
        return self.activo

    def tiene_rol(self, *roles):
        return self.rol.nombre in roles

    def __repr__(self):
        return f"<Usuario {self.correo}>"
