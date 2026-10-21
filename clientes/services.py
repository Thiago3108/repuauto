"""Lógica de negocio del módulo Gestión de clientes (US-02).

Aquí van las reglas del negocio: validar, consultar y guardar usando los modelos.
Las rutas llaman a estas funciones y las plantillas nunca tocan la base de datos.
"""
from sqlalchemy import and_, func, or_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Cliente, Rol, Usuario

CLIENTES_POR_PAGINA = 20


class CedulaRepetida(Exception):
    """La cédula ya es de otro cliente. existente es ese cliente, para poder mostrarlo."""

    def __init__(self, existente):
        super().__init__(f"La cédula {existente.cedula} ya es de {existente.nombre_completo}.")
        self.existente = existente


CON_TILDE = "áéíóúüñÁÉÍÓÚÜÑ"
SIN_TILDE = "aeiouunAEIOUUN"


class EnlaceRechazado(Exception):
    """No se puede enlazar la cuenta con el cliente. El mensaje dice por qué."""


def listar_clientes(pagina=1, busqueda=None):
    """Clientes ordenados por apellidos y nombres, de a CLIENTES_POR_PAGINA por página.

    Con busqueda (US-02 T3) deja solo los que coinciden, aunque sea en parte, por cédula,
    nombres, apellidos o teléfono. Cada palabra tiene que aparecer en alguno de esos
    campos, así "ana rueda" encuentra a Ana María Rueda. No distingue mayúsculas ni tildes.
    """
    consulta = db.select(Cliente)
    palabras = (busqueda or "").split()
    if palabras:
        campos = [Cliente.cedula, Cliente.nombres, Cliente.apellidos, Cliente.telefono]
        consulta = consulta.filter(and_(*(
            or_(*(_sin_tildes(campo).ilike(_patron(palabra), escape="\\") for campo in campos))
            for palabra in palabras
        )))
    consulta = consulta.order_by(Cliente.apellidos, Cliente.nombres, Cliente.id_cliente)
    return db.paginate(consulta, page=pagina, per_page=CLIENTES_POR_PAGINA, error_out=False)


def _sin_tildes(columna):
    return func.translate(columna, CON_TILDE, SIN_TILDE)


def _patron(palabra):
    """'%palabra%' sin tildes, escapando % y _ para que se busquen como texto."""
    palabra = palabra.translate(str.maketrans(CON_TILDE, SIN_TILDE))
    palabra = palabra.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{palabra}%"


def obtener_cliente(id_cliente):
    return db.session.get(Cliente, id_cliente)


def buscar_por_cedula(cedula):
    return db.session.scalar(db.select(Cliente).filter_by(cedula=cedula))


def crear_cliente(cedula, nombres, apellidos, telefono=None):
    """Crea un cliente de mostrador (sin cuenta). Lanza CedulaRepetida si la cédula ya existe."""
    existente = buscar_por_cedula(cedula)
    if existente is not None:
        raise CedulaRepetida(existente)

    cliente = Cliente(cedula=cedula, nombres=nombres, apellidos=apellidos, telefono=telefono or None)
    db.session.add(cliente)
    _guardar(cedula)
    return cliente


def actualizar_cliente(cliente, cedula, nombres, apellidos, telefono=None):
    """Cambia los datos de un cliente. Lanza CedulaRepetida si la cédula nueva es de otro."""
    existente = buscar_por_cedula(cedula)
    if existente is not None and existente.id_cliente != cliente.id_cliente:
        raise CedulaRepetida(existente)

    cliente.cedula = cedula
    cliente.nombres = nombres
    cliente.apellidos = apellidos
    cliente.telefono = telefono or None
    _guardar(cedula)
    return cliente


def _guardar(cedula):
    try:
        db.session.commit()
    except IntegrityError:
        # Otra persona guardó la misma cédula al mismo tiempo.
        db.session.rollback()
        raise CedulaRepetida(buscar_por_cedula(cedula))


# ---------- Enlazar la cuenta de un cliente (US-02 T4) ----------


def cuentas_sin_enlazar(correo):
    """Cuentas de cliente activas, sin cliente enlazado, cuyo correo contiene el texto buscado."""
    texto = (correo or "").strip().lower()
    if not texto:
        return []
    return db.session.scalars(
        db.select(Usuario)
        .join(Usuario.rol)
        .outerjoin(Usuario.cliente)
        .filter(
            Rol.nombre == "cliente",
            Usuario.activo.is_(True),
            Cliente.id_cliente.is_(None),
            Usuario.correo.ilike(_patron(texto), escape="\\"),
        )
        .order_by(Usuario.correo)
        .limit(10)
    ).all()


def enlazar_cuenta(cliente, id_usuario):
    """Enlaza una cuenta de cliente con un cliente, después de que el vendedor verificó su cédula.

    Una cuenta se enlaza a un solo cliente y un cliente tiene una sola cuenta.
    Lanza EnlaceRechazado si no se puede.
    """
    if cliente.usuario is not None:
        raise EnlaceRechazado("Este cliente ya tiene una cuenta enlazada.")

    usuario = db.session.get(Usuario, id_usuario)
    if usuario is None or not usuario.tiene_rol("cliente") or not usuario.activo:
        raise EnlaceRechazado("Esa cuenta no existe o no es una cuenta de cliente activa.")
    if usuario.cliente is not None:
        raise EnlaceRechazado(f"Esa cuenta ya está enlazada con {usuario.cliente.nombre_completo}.")

    cliente.usuario = usuario
    try:
        db.session.commit()
    except IntegrityError:
        # Otra persona enlazó la misma cuenta al mismo tiempo.
        db.session.rollback()
        raise EnlaceRechazado("Esa cuenta acaba de ser enlazada con otro cliente.")
    return usuario


def quitar_enlace(cliente):
    """Deja al cliente sin cuenta, por ejemplo si se enlazó la equivocada. La cuenta no se borra."""
    usuario = cliente.usuario
    cliente.usuario = None
    db.session.commit()
    return usuario
