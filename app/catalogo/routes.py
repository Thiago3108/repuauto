"""Controlador del módulo Catálogo de repuestos (US-05).

Las rutas reciben la petición, llaman a services.py y eligen la plantilla.
No consultan la base de datos directamente: eso es trabajo de services.py.
"""
from flask import jsonify, render_template, request

from app.auth.decoradores import rol_requerido
from app.catalogo import bp, services

TODOS = ("cliente", "vendedor", "administrador")


@bp.get("/")
@rol_requerido(*TODOS)
def index():
    """UI-04 Catálogo de repuestos con búsqueda, filtro por categoría y filtro en cascada
    por vehículo (marca -> línea -> año)."""
    busqueda = request.args.get("q", "").strip()
    id_categoria = request.args.get("id_categoria", type=int)
    id_marca = request.args.get("id_marca", type=int)
    linea = request.args.get("linea", "").strip() or None
    anio = request.args.get("anio", type=int)

    cascada = services.normalizar_filtro_vehiculo(id_marca, linea, anio)
    repuestos = services.consultar_catalogo(
        busqueda=busqueda,
        id_categoria=id_categoria,
        id_marca_vehiculo=cascada["id_marca"],
        linea=cascada["linea"],
        anio=cascada["anio"],
    )

    return render_template(
        "catalogo/index.html",
        repuestos=repuestos,
        categorias=services.listar_categorias(),
        marcas_vehiculo=services.listar_marcas_vehiculo(),
        busqueda=busqueda,
        id_categoria=id_categoria,
        id_marca=cascada["id_marca"],
        linea=cascada["linea"],
        anio=cascada["anio"],
        lineas=cascada["lineas"],
        anios=cascada["anios"],
    )


@bp.get("/vehiculos-cascada")
@rol_requerido(*TODOS)
def vehiculos_cascada():
    """Devuelve en JSON las líneas y años disponibles según la marca y línea seleccionadas."""
    id_marca = request.args.get("id_marca", type=int)
    linea = request.args.get("linea", "").strip() or None
    cascada = services.normalizar_filtro_vehiculo(id_marca, linea)
    return jsonify({"lineas": cascada["lineas"], "anios": cascada["anios"]})
