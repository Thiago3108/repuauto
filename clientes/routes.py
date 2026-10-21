"""Controlador del módulo Gestión de clientes (US-02).

Las rutas reciben la petición, llaman a services.py y eligen la plantilla.
No consultan la base de datos directamente: eso es trabajo de services.py.
"""
from flask import abort, flash, redirect, render_template, request, url_for

from app.auth.decoradores import rol_requerido
from app.clientes import bp, services
from app.clientes.forms import ClienteForm, EnlazarCuentaForm

PERSONAL = ("vendedor", "administrador")


@bp.get("/")
@rol_requerido(*PERSONAL)
def index():
    """UI-08 Gestión de clientes: la lista, con búsqueda por nombre, cédula o teléfono."""
    pagina = request.args.get("pagina", 1, type=int)
    busqueda = request.args.get("q", "").strip()
    return render_template(
        "clientes/lista.html",
        clientes=services.listar_clientes(pagina, busqueda),
        busqueda=busqueda,
    )


@bp.route("/nuevo", methods=["GET", "POST"])
@rol_requerido(*PERSONAL)
def nuevo():
    form = ClienteForm()
    if form.validate_on_submit():
        try:
            cliente = services.crear_cliente(
                form.cedula.data, form.nombres.data, form.apellidos.data, form.telefono.data
            )
        except services.CedulaRepetida as repetida:
            # Criterio de US-02: si la cédula ya existe, se muestra ese cliente.
            flash(f"Ya existe un cliente con la cédula {repetida.existente.cedula}. Estos son sus datos.", "warning")
            return redirect(url_for("clientes.detalle", id_cliente=repetida.existente.id_cliente))
        flash(f"Se registró a {cliente.nombre_completo}.", "success")
        return redirect(url_for("clientes.detalle", id_cliente=cliente.id_cliente))

    return render_template("clientes/formulario.html", form=form, cliente=None)


@bp.get("/<int:id_cliente>")
@rol_requerido(*PERSONAL)
def detalle(id_cliente):
    return render_template("clientes/detalle.html", cliente=_cliente_o_404(id_cliente))


@bp.route("/<int:id_cliente>/editar", methods=["GET", "POST"])
@rol_requerido(*PERSONAL)
def editar(id_cliente):
    cliente = _cliente_o_404(id_cliente)
    form = ClienteForm(obj=cliente)
    if form.validate_on_submit():
        try:
            services.actualizar_cliente(
                cliente, form.cedula.data, form.nombres.data, form.apellidos.data, form.telefono.data
            )
        except services.CedulaRepetida as repetida:
            form.cedula.errors.append(f"Esta cédula ya es de {repetida.existente.nombre_completo}.")
        else:
            flash("Se guardaron los cambios.", "success")
            return redirect(url_for("clientes.detalle", id_cliente=cliente.id_cliente))

    return render_template("clientes/formulario.html", form=form, cliente=cliente)


@bp.route("/<int:id_cliente>/enlazar", methods=["GET", "POST"])
@rol_requerido(*PERSONAL)
def enlazar(id_cliente):
    """US-02 T4: enlazar la cuenta de un cliente que verificó su cédula en persona."""
    cliente = _cliente_o_404(id_cliente)
    if cliente.usuario is not None:
        flash("Este cliente ya tiene una cuenta enlazada.", "info")
        return redirect(url_for("clientes.detalle", id_cliente=cliente.id_cliente))

    correo = request.args.get("correo", "").strip()
    form = EnlazarCuentaForm()
    if form.validate_on_submit():
        try:
            usuario = services.enlazar_cuenta(cliente, int(form.id_usuario.data))
        except (ValueError, services.EnlaceRechazado) as error:
            mensaje = str(error) if isinstance(error, services.EnlaceRechazado) else "Elige una cuenta de la lista."
            flash(mensaje, "danger")
        else:
            flash(f"Se enlazó la cuenta {usuario.correo} con {cliente.nombre_completo}.", "success")
            return redirect(url_for("clientes.detalle", id_cliente=cliente.id_cliente))

    return render_template(
        "clientes/enlazar.html",
        cliente=cliente,
        correo=correo,
        cuentas=services.cuentas_sin_enlazar(correo),
        form=form,
    )


@bp.post("/<int:id_cliente>/quitar-enlace")
@rol_requerido(*PERSONAL)
def quitar_enlace(id_cliente):
    cliente = _cliente_o_404(id_cliente)
    usuario = services.quitar_enlace(cliente)
    if usuario is not None:
        flash(f"Se quitó el enlace con la cuenta {usuario.correo}. La cuenta sigue existiendo.", "info")
    return redirect(url_for("clientes.detalle", id_cliente=cliente.id_cliente))


def _cliente_o_404(id_cliente):
    cliente = services.obtener_cliente(id_cliente)
    if cliente is None:
        abort(404)
    return cliente
