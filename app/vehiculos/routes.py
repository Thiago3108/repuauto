"""Controlador del módulo Gestión de vehículos (US-03).

Las rutas reciben la petición, llaman a services.py y eligen la plantilla.
No consultan la base de datos directamente: eso es trabajo de services.py.

Solo el administrador entra a este módulo (UI-11, decisión D3).
"""
from flask import abort, flash, redirect, render_template, request, url_for

from app.auth.decoradores import rol_requerido
from app.vehiculos import bp, services
from app.vehiculos.forms import VehiculoForm


def _datos(form):
    return {
        "marca": form.marca.data,
        "linea": form.linea.data,
        "referencia": form.referencia.data,
        "anio": form.anio.data,
    }


def _vehiculo_o_404(id_vehiculo):
    vehiculo = services.obtener_vehiculo(id_vehiculo)
    if vehiculo is None:
        abort(404)
    return vehiculo


@bp.route("/", methods=["GET", "POST"])
@rol_requerido("administrador")
def index():
    """UI-11 Gestión de vehículos: lista, búsqueda y registro de vehículos."""
    form = VehiculoForm()
    if form.validate_on_submit():
        try:
            vehiculo = services.crear_vehiculo(**_datos(form))
        except services.VehiculoRechazado as rechazo:
            getattr(form, rechazo.campo).errors.append(rechazo.mensaje)
        else:
            flash(f"Vehículo registrado: {vehiculo.descripcion}.", "success")
            return redirect(url_for("vehiculos.index"))

    busqueda = request.args.get("q", "").strip()
    return render_template(
        "vehiculos/index.html",
        form=form,
        vehiculos=services.listar_vehiculos(busqueda),
        marcas=services.listar_marcas(),
        busqueda=busqueda,
    )


@bp.route("/<int:id_vehiculo>/editar", methods=["GET", "POST"])
@rol_requerido("administrador")
def editar(id_vehiculo):
    """UI-11: cambiar los datos de un vehículo."""
    vehiculo = _vehiculo_o_404(id_vehiculo)
    form = VehiculoForm()
    if request.method == "GET":
        form.marca.data = vehiculo.marca.nombre
        form.linea.data = vehiculo.linea
        form.referencia.data = vehiculo.referencia
        form.anio.data = str(vehiculo.anio)

    if form.validate_on_submit():
        try:
            services.actualizar_vehiculo(vehiculo, **_datos(form))
        except services.VehiculoRechazado as rechazo:
            getattr(form, rechazo.campo).errors.append(rechazo.mensaje)
        else:
            flash(f"Vehículo actualizado: {vehiculo.descripcion}.", "success")
            return redirect(url_for("vehiculos.index"))

    return render_template(
        "vehiculos/editar.html", form=form, vehiculo=vehiculo, marcas=services.listar_marcas()
    )


@bp.post("/<int:id_vehiculo>/eliminar")
@rol_requerido("administrador")
def eliminar(id_vehiculo):
    """UI-11: eliminar un vehículo. Sus compatibilidades se van con él; los repuestos no."""
    vehiculo = _vehiculo_o_404(id_vehiculo)
    descripcion = vehiculo.descripcion
    services.eliminar_vehiculo(vehiculo)
    flash(f"Vehículo eliminado: {descripcion}.", "success")
    return redirect(url_for("vehiculos.index"))
