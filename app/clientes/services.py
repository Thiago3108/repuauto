"""Lógica de negocio del módulo Gestión de clientes (US-02).

Aquí van las reglas del negocio: validar, consultar y guardar usando los modelos.
Las rutas llaman a estas funciones y las plantillas nunca tocan la base de datos.
"""
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Cliente

CLIENTES_POR_PAGINA = 20


class CedulaRepetida(Exception):
    """La cédula ya es de otro cliente. existente es ese cliente, para poder mostrarlo."""

    def __init__(self, existente):
        super().__init__(f"La cédula {existente.cedula} ya es de {existente.nombre_completo}.")
        self.existente = existente


def listar_clientes(pagina=1):
    """Clientes ordenados por apellidos y nombres, de a CLIENTES_POR_PAGINA por página."""
    consulta = db.select(Cliente).order_by(Cliente.apellidos, Cliente.nombres, Cliente.id_cliente)
    return db.paginate(consulta, page=pagina, per_page=CLIENTES_POR_PAGINA, error_out=False)


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
