"""Lógica de negocio del módulo Gestión de clientes (US-02).

Aquí van las reglas del negocio: validar, consultar y guardar usando los modelos.
Las rutas llaman a estas funciones y las plantillas nunca tocan la base de datos.
"""
from sqlalchemy import and_, func, or_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Cliente

CLIENTES_POR_PAGINA = 20


class CedulaRepetida(Exception):
    """La cédula ya es de otro cliente. existente es ese cliente, para poder mostrarlo."""

    def __init__(self, existente):
        super().__init__(f"La cédula {existente.cedula} ya es de {existente.nombre_completo}.")
        self.existente = existente


CON_TILDE = "áéíóúüñÁÉÍÓÚÜÑ"
SIN_TILDE = "aeiouunAEIOUUN"


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
