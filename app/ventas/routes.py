"""Controlador del módulo Ventas (US-06 y US-08).

Las rutas reciben la petición, llaman a services.py y eligen la plantilla.
No consultan la base de datos directamente: eso es trabajo de services.py.
"""
from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.auth.decoradores import rol_requerido
from app.models.venta import ESTADOS_DE_VENTA
from app.ventas import bp, services
from app.ventas.forms import VentaForm

PERSONAL = ("vendedor", "administrador")


@bp.get("/")
@rol_requerido(*PERSONAL)
def index():
    """UI-07 Ventas registradas, con filtro por estado, para completarlas o cancelarlas."""
    estado = request.args.get("estado", "")
    if estado not in ESTADOS_DE_VENTA:
        estado = ""
    return render_template(
        "ventas/lista.html", ventas=services.listar_ventas(estado), estado=estado, estados=ESTADOS_DE_VENTA,
    )


@bp.route("/nueva", methods=["GET", "POST"])
@rol_requerido(*PERSONAL)
def nueva():
    """UI-06 Registro de venta."""
    form = VentaForm()
    if request.method == "GET" and request.args.get("cedula"):
        form.cedula.data = request.args["cedula"]
    repuestos = services.repuestos_para_vender()
    form.poner_repuestos(repuestos)

    sin_cliente = False
    if form.validate_on_submit():
        cliente = services.buscar_cliente(form.cedula.data)
        if cliente is None:
            sin_cliente = True
            form.cedula.errors.append("No hay un cliente con esta cédula. Regístralo primero.")
        else:
            try:
                venta = services.registrar_venta(
                    cliente, current_user._get_current_object(), form.lineas_elegidas(),
                    form.metodo_pago.data, completada=form.estado.data == "Completada",
                )
            except services.VentaRechazada as rechazo:
                flash(rechazo.mensaje, "danger")
            else:
                flash(f"Se registró la venta #{venta.id_venta} por ${venta.total:,.2f}.", "success")
                return redirect(url_for("ventas.detalle", id_venta=venta.id_venta))

    return render_template(
        "ventas/nueva.html",
        form=form,
        precios={r.id_repuesto: float(r.precio_venta) for r in repuestos},
        sin_cliente=sin_cliente,
    )


@bp.get("/<int:id_venta>")
@rol_requerido(*PERSONAL)
def detalle(id_venta):
    """Confirmación y detalle de una venta."""
    venta = services.obtener_venta(id_venta)
    if venta is None:
        abort(404)
    return render_template("ventas/detalle.html", venta=venta)


@bp.post("/<int:id_venta>/completar")
@rol_requerido(*PERSONAL)
def completar(id_venta):
    return _cambiar_estado(id_venta, services.completar_venta, "Se completó la venta #{}.")


@bp.post("/<int:id_venta>/cancelar")
@rol_requerido(*PERSONAL)
def cancelar(id_venta):
    return _cambiar_estado(id_venta, services.cancelar_venta, "Se canceló la venta #{} y se devolvió el stock.")


def _cambiar_estado(id_venta, cambio, mensaje):
    try:
        venta = cambio(id_venta)
    except services.VentaRechazada as rechazo:
        flash(rechazo.mensaje, "warning")
    else:
        if venta is None:
            abort(404)
        flash(mensaje.format(venta.id_venta), "success")
    # Solo se vuelve a una página de ventas, para que nadie use el formulario para redirigir a otro sitio.
    volver = request.form.get("volver", "")
    if not volver.startswith("/ventas/"):
        volver = url_for("ventas.detalle", id_venta=id_venta)
    return redirect(volver)
