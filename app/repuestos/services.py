
"""Lógica de negocio del módulo Repuestos y stock (US-04)."""

from decimal import Decimal, InvalidOperation

from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from app.extensions import db
from app.models import Categoria, MarcaRepuesto, Repuesto


class ErrorRepuesto(Exception):
    """Error de validación al gestionar un repuesto."""


def listar_repuestos(busqueda=None, incluir_inactivos=False):
    """Lista repuestos por código o nombre."""
    consulta = db.select(Repuesto).join(Repuesto.categoria).join(Repuesto.marca)

    if not incluir_inactivos:
        consulta = consulta.filter(Repuesto.activo.is_(True))

    texto = (busqueda or "").strip()
    if texto:
        texto_escapado = texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        patron = f"%{texto_escapado}%"
        consulta = consulta.filter(
            or_(
                Repuesto.codigo.ilike(patron, escape="\\"),
                Repuesto.nombre.ilike(patron, escape="\\"),
                Categoria.nombre.ilike(patron, escape="\\"),
                MarcaRepuesto.nombre.ilike(patron, escape="\\"),
            )
        )

    consulta = consulta.order_by(Repuesto.nombre, Repuesto.id_repuesto)
    return db.session.scalars(consulta).all()


def obtener_repuesto(id_repuesto):
    """Busca un repuesto por su identificador."""
    return db.session.get(Repuesto, id_repuesto)


def listar_categorias():
    """Devuelve las categorías ordenadas por nombre."""
    return db.session.scalars(
        db.select(Categoria).order_by(Categoria.nombre)
    ).all()


def listar_marcas():
    """Devuelve las marcas de repuestos ordenadas por nombre."""
    return db.session.scalars(
        db.select(MarcaRepuesto).order_by(MarcaRepuesto.nombre)
    ).all()


def listar_stock_bajo():
    """Repuestos activos cuyo stock está por debajo del mínimo."""
    return db.session.scalars(
        db.select(Repuesto)
        .filter(
            Repuesto.activo.is_(True),
            Repuesto.stock_actual < Repuesto.stock_minimo,
        )
        .order_by(Repuesto.stock_actual, Repuesto.nombre)
    ).all()


def crear_repuesto(
    codigo,
    nombre,
    precio_venta,
    id_categoria,
    id_marca_repuesto,
    descripcion=None,
    stock_actual=0,
    stock_minimo=0,
):
    """Registra un repuesto después de validar sus datos."""
    codigo = (codigo or "").strip()
    nombre = (nombre or "").strip()

    if not codigo or len(codigo) > 30:
        raise ErrorRepuesto("El código es obligatorio y admite máximo 30 caracteres.")
    if not nombre or len(nombre) > 100:
        raise ErrorRepuesto("El nombre es obligatorio y admite máximo 100 caracteres.")

    try:
        precio = Decimal(str(precio_venta))
        if not precio.is_finite() or precio < 0 or precio.as_tuple().exponent < -2:
            raise InvalidOperation
    except (InvalidOperation, ValueError, TypeError):
        raise ErrorRepuesto("El precio debe ser un número válido, no negativo y con máximo dos decimales.")

    try:
        stock_actual = int(stock_actual)
        stock_minimo = int(stock_minimo)
        id_categoria = int(id_categoria)
        id_marca_repuesto = int(id_marca_repuesto)
    except (ValueError, TypeError):
        raise ErrorRepuesto("La categoría, marca y cantidades deben ser valores enteros válidos.")

    if stock_actual < 0 or stock_minimo < 0:
        raise ErrorRepuesto("Las cantidades de stock no pueden ser negativas.")

    if db.session.scalar(
        db.select(Repuesto.id_repuesto).filter_by(codigo=codigo)
    ) is not None:
        raise ErrorRepuesto("Ya existe un repuesto con ese código.")

    categoria = db.session.get(Categoria, id_categoria)
    marca = db.session.get(MarcaRepuesto, id_marca_repuesto)

    if categoria is None:
        raise ErrorRepuesto("La categoría seleccionada no existe.")
    if marca is None:
        raise ErrorRepuesto("La marca de repuesto seleccionada no existe.")

    repuesto = Repuesto(
        codigo=codigo,
        nombre=nombre,
        descripcion=(descripcion or "").strip() or None,
        precio_venta=precio,
        stock_actual=stock_actual,
        stock_minimo=stock_minimo,
        id_categoria=id_categoria,
        id_marca_repuesto=id_marca_repuesto,
        activo=True,
    )

    db.session.add(repuesto)
    _guardar()
    return repuesto


def actualizar_repuesto(
    repuesto,
    codigo,
    nombre,
    precio_venta,
    id_categoria,
    id_marca_repuesto,
    descripcion=None,
    stock_minimo=None,
):
    """Actualiza los datos del repuesto sin alterar el stock actual."""
    nuevo = crear_datos_validados(
        codigo, nombre, precio_venta, id_categoria,
        id_marca_repuesto, descripcion,
    )

    existente = db.session.scalar(
        db.select(Repuesto.id_repuesto).filter_by(codigo=nuevo["codigo"])
    )
    if existente is not None and existente != repuesto.id_repuesto:
        raise ErrorRepuesto("Ya existe otro repuesto con ese código.")

    if stock_minimo is not None:
        try:
            stock_minimo = int(stock_minimo)
        except (ValueError, TypeError):
            raise ErrorRepuesto("El stock mínimo debe ser un entero.")
        if stock_minimo < 0:
            raise ErrorRepuesto("El stock mínimo no puede ser negativo.")
        repuesto.stock_minimo = stock_minimo

    repuesto.codigo = nuevo["codigo"]
    repuesto.nombre = nuevo["nombre"]
    repuesto.precio_venta = nuevo["precio_venta"]
    repuesto.descripcion = nuevo["descripcion"]
    repuesto.id_categoria = nuevo["id_categoria"]
    repuesto.id_marca_repuesto = nuevo["id_marca_repuesto"]

    _guardar()
    return repuesto


def crear_datos_validados(
    codigo, nombre, precio_venta, id_categoria,
    id_marca_repuesto, descripcion=None,
):
    """Valida los datos comunes de una edición."""
    codigo = (codigo or "").strip()
    nombre = (nombre or "").strip()

    if not codigo or len(codigo) > 30:
        raise ErrorRepuesto("El código es obligatorio y admite máximo 30 caracteres.")
    if not nombre or len(nombre) > 100:
        raise ErrorRepuesto("El nombre es obligatorio y admite máximo 100 caracteres.")

    try:
        precio = Decimal(str(precio_venta))
        if not precio.is_finite() or precio < 0 or precio.as_tuple().exponent < -2:
            raise InvalidOperation
        id_categoria = int(id_categoria)
        id_marca_repuesto = int(id_marca_repuesto)
    except (InvalidOperation, ValueError, TypeError):
        raise ErrorRepuesto("Revisa el precio, la categoría y la marca.")

    if db.session.get(Categoria, id_categoria) is None:
        raise ErrorRepuesto("La categoría seleccionada no existe.")
    if db.session.get(MarcaRepuesto, id_marca_repuesto) is None:
        raise ErrorRepuesto("La marca seleccionada no existe.")

    return {
        "codigo": codigo,
        "nombre": nombre,
        "precio_venta": precio,
        "id_categoria": id_categoria,
        "id_marca_repuesto": id_marca_repuesto,
        "descripcion": (descripcion or "").strip() or None,
    }


def ajustar_stock(repuesto, cantidad, motivo=None):
    """Suma o resta existencias sin permitir stock negativo."""
    try:
        cantidad = int(cantidad)
    except (ValueError, TypeError):
        raise ErrorRepuesto("La cantidad debe ser un entero.")

    if cantidad == 0:
        raise ErrorRepuesto("El ajuste debe ser diferente de cero.")

    nuevo_stock = repuesto.stock_actual + cantidad
    if nuevo_stock < 0:
        raise ErrorRepuesto("No hay existencias suficientes para ese ajuste.")

    repuesto.stock_actual = nuevo_stock
    _guardar()
    return repuesto


def desactivar_repuesto(repuesto):
    """Desactiva un repuesto sin eliminarlo de la base de datos."""
    repuesto.activo = False
    _guardar()
    return repuesto


def _guardar():
    """Guarda los cambios y controla conflictos de integridad."""
    try:
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        raise ErrorRepuesto(
            "No se pudo guardar. Comprueba que el código y los datos sean válidos."
        ) from error
