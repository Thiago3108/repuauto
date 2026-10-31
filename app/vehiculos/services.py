"""Lógica de negocio del módulo Gestión de vehículos (US-03).

Aquí van las reglas del negocio: validar, consultar y guardar usando los modelos.
Las rutas llaman a estas funciones y las plantillas nunca tocan la base de datos.

Reglas de US-03:
- Un vehículo tiene marca, línea, referencia opcional y un año de 4 dígitos.
- Las marcas de vehículo van aparte de las marcas de repuesto. Si el administrador
  escribe una marca que no existe, se crea; si ya existe (sin importar mayúsculas),
  se reutiliza.
- No se repite un vehículo con la misma marca, línea, referencia y año.
- A cada vehículo se le asocian los repuestos compatibles sin duplicarlos. Al eliminar
  el vehículo se borran sus compatibilidades, pero no los repuestos.
"""
from datetime import date

from sqlalchemy import String, cast, func, or_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Categoria, MarcaRepuesto, MarcaVehiculo, Repuesto, RepuestoVehiculo, Vehiculo

ANIO_MINIMO = 1900


class VehiculoRechazado(Exception):
    """La operación no se puede completar. campo dice qué campo del formulario lo causó."""

    def __init__(self, campo, mensaje):
        super().__init__(mensaje)
        self.campo = campo
        self.mensaje = mensaje


def limpiar(texto):
    """Quita los espacios de los extremos y deja uno solo entre palabras. Vacío -> None."""
    if texto is None:
        return None
    texto = " ".join(str(texto).split())
    return texto or None


def anio_maximo():
    """Se aceptan los modelos del año siguiente, que salen a la venta antes de tiempo."""
    return date.today().year + 1


def validar_anio(anio):
    """Devuelve el año como entero, o lanza VehiculoRechazado si no es válido."""
    try:
        anio = int(anio)
    except (TypeError, ValueError):
        raise VehiculoRechazado("anio", "El año debe ser un número de 4 dígitos.")
    if not ANIO_MINIMO <= anio <= anio_maximo():
        raise VehiculoRechazado("anio", f"El año debe estar entre {ANIO_MINIMO} y {anio_maximo()}.")
    return anio


# ---------- Marcas ----------

def listar_marcas():
    return db.session.scalars(db.select(MarcaVehiculo).order_by(MarcaVehiculo.nombre)).all()


def buscar_marca(nombre):
    """Busca una marca por nombre sin importar mayúsculas ni espacios de más."""
    nombre = limpiar(nombre)
    if not nombre:
        return None
    return db.session.scalar(
        db.select(MarcaVehiculo).where(func.lower(MarcaVehiculo.nombre) == nombre.lower())
    )


def obtener_o_crear_marca(nombre):
    """Devuelve la marca con ese nombre, y si no existe la crea. No hace commit."""
    nombre = limpiar(nombre)
    if not nombre:
        raise VehiculoRechazado("marca", "Escribe la marca del vehículo.")
    if len(nombre) > 60:
        raise VehiculoRechazado("marca", "La marca puede tener máximo 60 caracteres.")
    marca = buscar_marca(nombre)
    if marca is None:
        marca = MarcaVehiculo(nombre=nombre)
        db.session.add(marca)
    return marca


# ---------- Vehículos ----------

def listar_vehiculos(busqueda=None):
    """Vehículos ordenados por marca, línea y año. La búsqueda acepta coincidencias parciales
    en la marca, la línea, la referencia o el año."""
    consulta = (
        db.select(Vehiculo)
        .join(Vehiculo.marca)
        .order_by(MarcaVehiculo.nombre, Vehiculo.linea, Vehiculo.anio.desc(), Vehiculo.referencia)
    )
    busqueda = limpiar(busqueda)
    if busqueda:
        patron = f"%{busqueda}%"
        consulta = consulta.where(or_(
            MarcaVehiculo.nombre.ilike(patron),
            Vehiculo.linea.ilike(patron),
            Vehiculo.referencia.ilike(patron),
            cast(Vehiculo.anio, String).ilike(patron),
        ))
    return db.session.scalars(consulta).all()


def obtener_vehiculo(id_vehiculo):
    return db.session.get(Vehiculo, id_vehiculo)


def _buscar_duplicado(marca, linea, referencia, anio, excepto=None):
    """El vehículo con los mismos datos (sin importar mayúsculas), si ya existe."""
    if marca.id_marca_vehiculo is None:
        return None  # La marca es nueva: no puede haber vehículos con ella.
    consulta = db.select(Vehiculo).where(
        Vehiculo.id_marca_vehiculo == marca.id_marca_vehiculo,
        func.lower(Vehiculo.linea) == linea.lower(),
        func.lower(func.coalesce(Vehiculo.referencia, "")) == (referencia or "").lower(),
        Vehiculo.anio == anio,
    )
    if excepto is not None:
        consulta = consulta.where(Vehiculo.id_vehiculo != excepto.id_vehiculo)
    return db.session.scalar(consulta)


def _datos_validos(marca, linea, anio, referencia):
    linea = limpiar(linea)
    referencia = limpiar(referencia)
    if not linea:
        raise VehiculoRechazado("linea", "Escribe la línea del vehículo.")
    if len(linea) > 60:
        raise VehiculoRechazado("linea", "La línea puede tener máximo 60 caracteres.")
    if referencia and len(referencia) > 60:
        raise VehiculoRechazado("referencia", "La referencia puede tener máximo 60 caracteres.")
    anio = validar_anio(anio)
    with db.session.no_autoflush:
        marca = obtener_o_crear_marca(marca)
    return marca, linea, anio, referencia


def _guardar():
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise VehiculoRechazado("marca", "No se pudo guardar: otra persona guardó la misma marca. Intenta de nuevo.")


def crear_vehiculo(marca, linea, anio, referencia=None):
    """Registra un vehículo (US-03 T2). Lanza VehiculoRechazado si los datos no sirven."""
    try:
        marca, linea, anio, referencia = _datos_validos(marca, linea, anio, referencia)
        if _buscar_duplicado(marca, linea, referencia, anio) is not None:
            raise VehiculoRechazado("linea", "Ese vehículo ya está registrado.")
    except VehiculoRechazado:
        db.session.rollback()
        raise
    vehiculo = Vehiculo(marca=marca, linea=linea, referencia=referencia, anio=anio)
    db.session.add(vehiculo)
    _guardar()
    return vehiculo


def actualizar_vehiculo(vehiculo, marca, linea, anio, referencia=None):
    """Cambia los datos de un vehículo. Lanza VehiculoRechazado si los datos no sirven."""
    try:
        marca, linea, anio, referencia = _datos_validos(marca, linea, anio, referencia)
        if _buscar_duplicado(marca, linea, referencia, anio, excepto=vehiculo) is not None:
            raise VehiculoRechazado("linea", "Ya hay otro vehículo registrado con esos datos.")
    except VehiculoRechazado:
        db.session.rollback()
        raise
    vehiculo.marca = marca
    vehiculo.linea = linea
    vehiculo.referencia = referencia
    vehiculo.anio = anio
    _guardar()
    return vehiculo


def eliminar_vehiculo(vehiculo):
    """Elimina un vehículo. Sus compatibilidades se borran en cascada (repuesto_vehiculo,
    US-03 T3), pero los repuestos no se tocan."""
    db.session.delete(vehiculo)
    db.session.commit()
    db.session.expire_all()


# ---------- Repuestos compatibles (US-03 T3) ----------

def _id_repuesto(repuesto_o_id):
    if isinstance(repuesto_o_id, Repuesto):
        return repuesto_o_id.id_repuesto
    try:
        return int(repuesto_o_id)
    except (TypeError, ValueError):
        raise VehiculoRechazado("id_repuesto", "Elige un repuesto válido.")


def listar_repuestos_compatibles(vehiculo):
    """Repuestos asociados con el vehículo, ordenados por nombre y código."""
    consulta = (
        db.select(Repuesto)
        .join(RepuestoVehiculo, RepuestoVehiculo.id_repuesto == Repuesto.id_repuesto)
        .where(RepuestoVehiculo.id_vehiculo == vehiculo.id_vehiculo)
        .order_by(Repuesto.nombre, Repuesto.codigo)
    )
    return db.session.scalars(consulta).all()


def listar_repuestos_disponibles(vehiculo, busqueda=None):
    """Repuestos activos que todavía no están asociados con este vehículo."""
    ya_asociados = (
        db.select(RepuestoVehiculo.id_repuesto)
        .where(RepuestoVehiculo.id_vehiculo == vehiculo.id_vehiculo)
    )
    consulta = (
        db.select(Repuesto)
        .join(Repuesto.categoria)
        .join(Repuesto.marca)
        .where(Repuesto.activo.is_(True), Repuesto.id_repuesto.not_in(ya_asociados))
        .order_by(Repuesto.nombre, Repuesto.codigo)
    )
    busqueda = limpiar(busqueda)
    if busqueda:
        patron = f"%{busqueda}%"
        consulta = consulta.where(or_(
            Repuesto.codigo.ilike(patron),
            Repuesto.nombre.ilike(patron),
            Categoria.nombre.ilike(patron),
            MarcaRepuesto.nombre.ilike(patron),
        ))
    return db.session.scalars(consulta).all()


def asociar_repuesto(vehiculo, repuesto_o_id):
    """Asocia un repuesto compatible a un vehículo (US-03 T3) sin duplicar la relación."""
    id_repuesto = _id_repuesto(repuesto_o_id)
    repuesto = db.session.get(Repuesto, id_repuesto)
    if repuesto is None or not repuesto.activo:
        raise VehiculoRechazado("id_repuesto", "Elige un repuesto activo del catálogo.")

    if db.session.get(RepuestoVehiculo, (repuesto.id_repuesto, vehiculo.id_vehiculo)) is not None:
        raise VehiculoRechazado("id_repuesto", "Ese repuesto ya está asociado con este vehículo.")

    db.session.add(RepuestoVehiculo(id_repuesto=repuesto.id_repuesto, id_vehiculo=vehiculo.id_vehiculo))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise VehiculoRechazado("id_repuesto", "Ese repuesto ya está asociado con este vehículo.")
    db.session.expire(vehiculo, ["repuestos"])
    return repuesto


def desasociar_repuesto(vehiculo, repuesto_o_id):
    """Quita la compatibilidad entre un vehículo y un repuesto. No borra el repuesto."""
    id_repuesto = _id_repuesto(repuesto_o_id)
    enlace = db.session.get(RepuestoVehiculo, (id_repuesto, vehiculo.id_vehiculo))
    if enlace is None:
        return False
    db.session.delete(enlace)
    db.session.commit()
    db.session.expire(vehiculo, ["repuestos"])
    return True
