"""Controlador del módulo Proveedores y compras (US-09).

Las rutas reciben la petición, llaman a services.py y eligen la plantilla.
No consultan la base de datos directamente: eso es trabajo de services.py.
Todo el módulo es solo para el administrador.
"""
from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.auth.decoradores import rol_requerido
from app.compras import bp, services
from app.compras.forms import CompraForm, ProveedorForm


@bp.get("/")
@rol_requerido("administrador")
def index():
    """UI-14 Proveedores y compras: las compras más recientes."""
    return render_template("compras/lista.html", compras=services.listar_compras())


@bp.route("/nueva", methods=["GET", "POST"])
@rol_requerido("administrador")
def nueva():
    """UI-14 Registrar una compra: las cantidades se suman al stock."""
    form = CompraForm()
    if request.method == "GET" and request.args.get("proveedor", type=int):
        form.id_proveedor.data = request.args.get("proveedor", type=int)
    proveedores = services.listar_proveedores()
    form.poner_opciones(proveedores, services.repuestos_para_comprar())

    if form.validate_on_submit():
        try:
            compra = services.registrar_compra(
                services.obtener_proveedor(form.id_proveedor.data),
                current_user._get_current_object(),
                form.lineas_elegidas(),
            )
        except services.CompraRechazada as rechazo:
            flash(rechazo.mensaje, "danger")
        else:
            flash(f"Se registró la compra #{compra.id_compra} por ${compra.total:,.2f} y se sumó al stock.", "success")
            return redirect(url_for("compras.detalle", id_compra=compra.id_compra))

    return render_template("compras/nueva.html", form=form, sin_proveedores=not proveedores)


@bp.get("/<int:id_compra>")
@rol_requerido("administrador")
def detalle(id_compra):
    compra = services.obtener_compra(id_compra)
    if compra is None:
        abort(404)
    return render_template("compras/detalle.html", compra=compra)


# ---------- Proveedores (US-09 T2) ----------


@bp.get("/proveedores")
@rol_requerido("administrador")
def proveedores():
    busqueda = request.args.get("q", "").strip()
    return render_template(
        "compras/proveedores.html", proveedores=services.listar_proveedores(busqueda), busqueda=busqueda,
    )


@bp.route("/proveedores/nuevo", methods=["GET", "POST"])
@rol_requerido("administrador")
def nuevo_proveedor():
    form = ProveedorForm()
    if form.validate_on_submit():
        try:
            proveedor = services.crear_proveedor(
                form.nit.data, form.nombre.data, form.telefono.data, form.correo.data
            )
        except services.NitRepetido as repetido:
            form.nit.errors.append(f"Este NIT ya es de {repetido.existente.nombre}.")
        else:
            flash(f"Se registró el proveedor {proveedor.nombre}.", "success")
            return redirect(url_for("compras.proveedores"))

    return render_template("compras/proveedor.html", form=form, proveedor=None)


@bp.route("/proveedores/<int:id_proveedor>/editar", methods=["GET", "POST"])
@rol_requerido("administrador")
def editar_proveedor(id_proveedor):
    proveedor = services.obtener_proveedor(id_proveedor)
    if proveedor is None:
        abort(404)
    form = ProveedorForm(obj=proveedor)
    if form.validate_on_submit():
        try:
            services.actualizar_proveedor(
                proveedor, form.nit.data, form.nombre.data, form.telefono.data, form.correo.data
            )
        except services.NitRepetido as repetido:
            form.nit.errors.append(f"Este NIT ya es de {repetido.existente.nombre}.")
        else:
            flash("Se guardaron los cambios.", "success")
            return redirect(url_for("compras.proveedores"))

    return render_template("compras/proveedor.html", form=form, proveedor=proveedor)
