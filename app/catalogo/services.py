"""Lógica de negocio del módulo Catálogo de repuestos (US-05).

Aquí van las reglas del negocio: validar, consultar y guardar usando los modelos.
Las rutas llaman a estas funciones y las plantillas nunca tocan la base de datos.

Claves de US-05:
- Solo aparecen los repuestos activos, con su disponibilidad (en stock o agotado).
- Se busca por nombre o código y se filtra por categoría.
- El filtro por vehículo va en cascada (US-05 T2): marca, luego línea y luego año.
"""
from sqlalchemy import func, or_

from app.extensions import db
from app.models import Categoria, MarcaRepuesto, MarcaVehiculo, Repuesto, RepuestoVehiculo, Vehiculo
from app.validadores import limpiar


def listar_categorias():
    """Categorías de repuestos ordenadas por nombre."""
    return db.session.scalars(db.select(Categoria).order_by(Categoria.nombre)).all()


def listar_marcas_vehiculo():
    """Marcas de vehículo ordenadas por nombre para el primer nivel del filtro en cascada."""
    return db.session.scalars(db.select(MarcaVehiculo).order_by(MarcaVehiculo.nombre)).all()


def listar_lineas_por_marca(id_marca_vehiculo):
    """Segundo nivel de la cascada (US-05 T2): líneas registradas para la marca elegida."""
    try:
        id_marca = int(id_marca_vehiculo)
    except (TypeError, ValueError):
        return []
    if db.session.get(MarcaVehiculo, id_marca) is None:
        return []
    consulta = (
        db.select(Vehiculo.linea)
        .where(Vehiculo.id_marca_vehiculo == id_marca)
        .distinct()
        .order_by(Vehiculo.linea)
    )
    return list(db.session.scalars(consulta).all())


def listar_anios_por_marca_y_linea(id_marca_vehiculo, linea):
    """Tercer nivel de la cascada (US-05 T2): años registrados para la marca y línea elegidas."""
    linea = limpiar(linea)
    if not linea:
        return []
    lineas_validas = {item.lower(): item for item in listar_lineas_por_marca(id_marca_vehiculo)}
    if linea.lower() not in lineas_validas:
        return []
    consulta = (
        db.select(Vehiculo.anio)
        .where(
            Vehiculo.id_marca_vehiculo == int(id_marca_vehiculo),
            func.lower(Vehiculo.linea) == linea.lower(),
        )
        .distinct()
        .order_by(Vehiculo.anio.desc())
    )
    return list(db.session.scalars(consulta).all())


def normalizar_filtro_vehiculo(id_marca_vehiculo=None, linea=None, anio=None):
    """Aplica la cascada Marca -> Línea -> Año (US-05 T2).

    - Si no hay una marca válida, se descartan línea y año.
    - Si la línea no pertenece a la marca elegida, se descartan línea y año.
    - Si el año no pertenece a la marca y línea elegidas, se descarta el año.
    """
    try:
        id_marca = int(id_marca_vehiculo) if id_marca_vehiculo else None
    except (TypeError, ValueError):
        id_marca = None

    if id_marca is None or db.session.get(MarcaVehiculo, id_marca) is None:
        return {
            "id_marca": None,
            "linea": None,
            "anio": None,
            "lineas": [],
            "anios": [],
        }

    lineas = listar_lineas_por_marca(id_marca)
    mapa_lineas = {item.lower(): item for item in lineas}
    linea_limpia = limpiar(linea)
    linea_valida = mapa_lineas.get(linea_limpia.lower()) if linea_limpia else None

    if linea_valida is None:
        return {
            "id_marca": id_marca,
            "linea": None,
            "anio": None,
            "lineas": lineas,
            "anios": [],
        }

    anios = listar_anios_por_marca_y_linea(id_marca, linea_valida)
    try:
        anio_int = int(anio) if anio else None
    except (TypeError, ValueError):
        anio_int = None
    anio_valido = anio_int if anio_int in anios else None

    return {
        "id_marca": id_marca,
        "linea": linea_valida,
        "anio": anio_valido,
        "lineas": lineas,
        "anios": anios,
    }


def consultar_catalogo(
    busqueda=None,
    id_categoria=None,
    id_marca_vehiculo=None,
    linea=None,
    anio=None,
):
    """Devuelve los repuestos activos que cumplen los filtros de texto, categoría y vehículo."""
    consulta = (
        db.select(Repuesto)
        .join(Repuesto.categoria)
        .join(Repuesto.marca)
        .where(Repuesto.activo.is_(True))
    )

    texto = limpiar(busqueda)
    if texto:
        texto_escapado = texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        patron = f"%{texto_escapado}%"
        consulta = consulta.where(
            or_(
                Repuesto.codigo.ilike(patron, escape="\\"),
                Repuesto.nombre.ilike(patron, escape="\\"),
            )
        )

    try:
        id_cat = int(id_categoria) if id_categoria else None
    except (TypeError, ValueError):
        id_cat = None
    if id_cat is not None:
        consulta = consulta.where(Repuesto.id_categoria == id_cat)

    cascada = normalizar_filtro_vehiculo(id_marca_vehiculo, linea, anio)
    if cascada["id_marca"] is not None:
        compatibles = (
            db.select(RepuestoVehiculo.id_repuesto)
            .join(Vehiculo, Vehiculo.id_vehiculo == RepuestoVehiculo.id_vehiculo)
            .where(Vehiculo.id_marca_vehiculo == cascada["id_marca"])
        )
        if cascada["linea"] is not None:
            compatibles = compatibles.where(func.lower(Vehiculo.linea) == cascada["linea"].lower())
        if cascada["anio"] is not None:
            compatibles = compatibles.where(Vehiculo.anio == cascada["anio"])
        consulta = consulta.where(Repuesto.id_repuesto.in_(compatibles))

    return db.session.scalars(
        consulta.order_by(Repuesto.nombre, Repuesto.codigo, MarcaRepuesto.nombre)
    ).all()
