"""Controlador del módulo Repuestos y stock (US-04).

Las rutas reciben la petición, llaman a services.py y eligen la plantilla.
No consultan la base de datos directamente: eso es trabajo de services.py.
"""

"""Rutas para gestionar repuestos y existencias (US-04)."""

from flask import abort, flash, redirect, render_template, request, url_for
from flask_wtf import FlaskForm

from app.auth.decoradores import rol_requerido
from app.repuestos import bp
from app.repuestos.forms import (
    AjustarStockForm,
    CrearRepuestoForm,
    RepuestoForm,
)
from app.repuestos import services


def _cargar_opciones(form):
    """Carga categorías y marcas en los campos desplegables."""
    form.id_categoria.choices = [
        (categoria.id_categoria, categoria.nombre)
        for categoria in services.listar_categorias()
    ]
    form.id_marca_repuesto.choices = [
        (marca.id_marca_repuesto, marca.nombre)
        for marca in services.listar_marcas()
    ]


def _obtener_repuesto_o_404(id_repuesto):
    repuesto = services.obtener_repuesto(id_repuesto)
    if repuesto is None:
        abort(404)
    return repuesto


@bp.get("/")
@rol_requerido("administrador")
def index():
    """UI-10: listado y gestión de repuestos."""
    busqueda = request.args.get("buscar", "").strip()
    incluir_inactivos = request.args.get("inactivos") == "1"

    repuestos = services.listar_repuestos(
        busqueda=busqueda,
        incluir_inactivos=incluir_inactivos,
    )

    return render_template(
        "repuestos/lista.html",
        repuestos=repuestos,
        busqueda=busqueda,
        incluir_inactivos=incluir_inactivos,
    )


@bp.route("/nuevo", methods=["GET", "POST"])
@rol_requerido("administrador")
def crear():
    """UI-10: registrar un repuesto."""
    form = CrearRepuestoForm()
    _cargar_opciones(form)

    if form.validate_on_submit():
        try:
            services.crear_repuesto(
                codigo=form.codigo.data,
                nombre=form.nombre.data,
                precio_venta=form.precio_venta.data,
                id_categoria=form.id_categoria.data,
                id_marca_repuesto=form.id_marca_repuesto.data,
                descripcion=form.descripcion.data,
                stock_actual=form.stock_actual.data,
                stock_minimo=form.stock_minimo.data,
            )
            flash("Repuesto creado correctamente.", "success")
            return redirect(url_for("repuestos.index"))
        except services.ErrorRepuesto as error:
            flash(str(error), "danger")

    return render_template("repuestos/formulario.html", form=form, titulo="Nuevo repuesto")


@bp.route("/<int:id_repuesto>/editar", methods=["GET", "POST"])
@rol_requerido("administrador")
def editar(id_repuesto):
    """UI-10: editar datos sin modificar las existencias actuales."""
    repuesto = _obtener_repuesto_o_404(id_repuesto)
    form = RepuestoForm()
    _cargar_opciones(form)

    if request.method == "GET":
        form.codigo.data = repuesto.codigo
        form.nombre.data = repuesto.nombre
        form.descripcion.data = repuesto.descripcion
        form.precio_venta.data = repuesto.precio_venta
        form.id_categoria.data = repuesto.id_categoria
        form.id_marca_repuesto.data = repuesto.id_marca_repuesto
        form.stock_minimo.data = repuesto.stock_minimo

    if form.validate_on_submit():
        try:
            services.actualizar_repuesto(
                repuesto=repuesto,
                codigo=form.codigo.data,
                nombre=form.nombre.data,
                precio_venta=form.precio_venta.data,
                id_categoria=form.id_categoria.data,
                id_marca_repuesto=form.id_marca_repuesto.data,
                descripcion=form.descripcion.data,
                stock_minimo=form.stock_minimo.data,
            )
            flash("Repuesto actualizado correctamente.", "success")
            return redirect(url_for("repuestos.index"))
        except services.ErrorRepuesto as error:
            flash(str(error), "danger")

    return render_template(
        "repuestos/formulario.html",
        form=form,
        titulo="Editar repuesto",
        repuesto=repuesto,
    )


@bp.get("/stock")
@rol_requerido("vendedor", "administrador")
def stock():
    """UI-09: consulta de existencias y alertas de stock bajo."""
    busqueda = request.args.get("buscar", "").strip()
    repuestos = services.listar_repuestos(busqueda=busqueda)
    alertas = services.listar_stock_bajo()

    return render_template(
        "repuestos/stock.html",
        repuestos=repuestos,
        alertas=alertas,
        busqueda=busqueda,
    )


@bp.route("/<int:id_repuesto>/ajustar-stock", methods=["GET", "POST"])
@rol_requerido("administrador")
def ajustar_stock(id_repuesto):
    """Ajustar las existencias sin permitir que queden negativas."""
    repuesto = _obtener_repuesto_o_404(id_repuesto)
    form = AjustarStockForm()

    if form.validate_on_submit():
        try:
            services.ajustar_stock(
                repuesto=repuesto,
                cantidad=form.cantidad.data,
                motivo=form.motivo.data,
            )
            flash("Stock actualizado correctamente.", "success")
            return redirect(url_for("repuestos.stock"))
        except services.ErrorRepuesto as error:
            flash(str(error), "danger")

    return render_template(
        "repuestos/ajustar_stock.html",
        form=form,
        repuesto=repuesto,
    )


@bp.post("/<int:id_repuesto>/desactivar")
@rol_requerido("administrador")
def desactivar(id_repuesto):
    """Desactivar un repuesto sin eliminarlo de la base de datos."""
    repuesto = _obtener_repuesto_o_404(id_repuesto)

    if not repuesto.activo:
        flash("El repuesto ya estaba desactivado.", "warning")
        return redirect(url_for("repuestos.index"))

    form = FlaskForm()
    if not form.validate_on_submit():
        abort(400)

    try:
        services.desactivar_repuesto(repuesto)
        flash("Repuesto desactivado del catálogo.", "success")
    except services.ErrorRepuesto as error:
        flash(str(error), "danger")

    return redirect(url_for("repuestos.index"))
