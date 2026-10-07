"""Lógica de negocio del módulo Cuentas y acceso (US-01).

Aquí van las reglas del negocio: validar, consultar y guardar usando los modelos.
Las rutas llaman a estas funciones y las plantillas nunca tocan la base de datos.
"""
import re

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import Rol, Usuario


def normalizar_correo(correo):
    """Los correos se guardan y se buscan sin espacios y en minúscula."""
    return correo.strip().lower()


def contrasena_segura(clave):
    """Regla de US-01: más de 8 caracteres, al menos un número y un carácter especial."""
    return (
        len(clave) > 8
        and re.search(r"\d", clave) is not None
        and re.search(r"[^A-Za-z0-9]", clave) is not None
    )


def buscar_por_correo(correo):
    return db.session.scalar(db.select(Usuario).filter_by(correo=normalizar_correo(correo)))


def cargar_usuario(id_usuario):
    """Lo usa Flask-Login en cada petición. Una cuenta desactivada pierde la sesión."""
    usuario = db.session.get(Usuario, int(id_usuario))
    if usuario is None or not usuario.activo:
        return None
    return usuario


def autenticar(correo, clave):
    """Devuelve el usuario si el correo y la contraseña son correctos y la cuenta está activa.

    Si algo falla devuelve None, sin decir qué: la pantalla muestra un mensaje genérico
    para no revelar qué correos tienen cuenta.
    """
    usuario = buscar_por_correo(correo)
    if usuario is None or not usuario.activo:
        return None
    if not check_password_hash(usuario.contrasena_hash, clave):
        return None
    return usuario


def crear_usuario(correo, clave, nombre, rol):
    """Crea una cuenta con la contraseña convertida en hash. No hace commit."""
    usuario = Usuario(
        correo=normalizar_correo(correo),
        contrasena_hash=generate_password_hash(clave),
        nombre=nombre.strip(),
        rol=db.session.scalar(db.select(Rol).filter_by(nombre=rol)),
    )
    db.session.add(usuario)
    return usuario
