"""Lógica de negocio del módulo Cuentas y acceso (US-01).

Aquí van las reglas del negocio: validar, consultar y guardar usando los modelos.
Las rutas llaman a estas funciones y las plantillas nunca tocan la base de datos.
"""
import re

from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import Cliente, Rol, Usuario


class RegistroRechazado(Exception):
    """No se puede crear la cuenta. campo dice qué campo del formulario lo causó."""

    def __init__(self, campo, mensaje):
        super().__init__(mensaje)
        self.campo = campo
        self.mensaje = mensaje


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


def registrar_cliente(nombres, apellidos, cedula, correo, clave, telefono=None):
    """Registro de cliente (US-01 T2). Guarda la cuenta y el cliente en una sola transacción.

    - Si la cédula es nueva, crea el cliente y lo enlaza a la cuenta.
    - Si la cédula ya es de un cliente de mostrador (sin cuenta), crea la cuenta sin
      enlazar: un vendedor la enlaza después verificando la cédula en persona (US-02 T4),
      para que nadie vea el historial de otro solo con conocer su cédula.
    - Si la cédula ya tiene cuenta o el correo ya está registrado, no guarda nada.

    Devuelve (usuario, enlazada). Lanza RegistroRechazado si no se puede registrar.
    """
    if buscar_por_correo(correo) is not None:
        raise RegistroRechazado("correo", "Ya existe una cuenta con este correo.")

    cliente = db.session.scalar(db.select(Cliente).filter_by(cedula=cedula))
    if cliente is not None and cliente.id_usuario is not None:
        raise RegistroRechazado("cedula", "Ya existe una cuenta con esta cédula. Inicia sesión.")

    usuario = crear_usuario(correo, clave, f"{nombres} {apellidos}"[:100], "cliente")
    enlazada = cliente is None
    if enlazada:
        db.session.add(Cliente(
            cedula=cedula, nombres=nombres, apellidos=apellidos,
            telefono=telefono or None, usuario=usuario,
        ))

    try:
        db.session.commit()
    except IntegrityError:
        # Otra persona se registró con el mismo correo o cédula al mismo tiempo.
        db.session.rollback()
        raise RegistroRechazado("correo", "Ya existe una cuenta con este correo o esta cédula.")
    return usuario, enlazada


def listar_vendedores():
    """Cuentas de vendedor para UI-13: primero las activas, luego por nombre."""
    return db.session.scalars(
        db.select(Usuario)
        .join(Usuario.rol)
        .filter(Rol.nombre == "vendedor")
        .order_by(Usuario.activo.desc(), Usuario.nombre)
    ).all()


def crear_vendedor(nombre, correo, clave):
    """El administrador crea una cuenta de vendedor (US-01 T4). Lanza RegistroRechazado si el correo ya existe."""
    if buscar_por_correo(correo) is not None:
        raise RegistroRechazado("correo", "Ya existe una cuenta con este correo.")
    usuario = crear_usuario(correo, clave, nombre, "vendedor")
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise RegistroRechazado("correo", "Ya existe una cuenta con este correo.")
    return usuario


def cambiar_estado_vendedor(id_usuario, activo):
    """Activa o desactiva una cuenta de vendedor. No se borran: sus ventas siguen apuntando a ella.

    Devuelve el vendedor, o None si no existe o no es vendedor.
    """
    usuario = db.session.get(Usuario, id_usuario)
    if usuario is None or not usuario.tiene_rol("vendedor"):
        return None
    usuario.activo = activo
    db.session.commit()
    return usuario
