"""Controlador del módulo Cuentas y acceso (US-01).

Las rutas reciben la petición, llaman a services.py y eligen la plantilla.
No consultan la base de datos directamente: eso es trabajo de services.py.
"""
from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from app.auth import bp, services
from app.auth.decoradores import rol_requerido
from app.auth.forms import LoginForm, RegistroForm
from app.extensions import login_manager

# Vistas que se abren sin iniciar sesión. Todas las demás lo exigen.
VISTAS_PUBLICAS = {"auth.login", "auth.registro", "static"}


@login_manager.user_loader
def cargar_usuario(id_usuario):
    return services.cargar_usuario(id_usuario)


@bp.before_app_request
def exigir_sesion():
    """Cualquier página, de cualquier módulo, pide iniciar sesión primero."""
    if request.endpoint in VISTAS_PUBLICAS or request.endpoint is None:
        return None
    if not current_user.is_authenticated:
        return login_manager.unauthorized()
    return None


@bp.route("/login", methods=["GET", "POST"])
def login():
    """UI-01 Iniciar sesión."""
    if current_user.is_authenticated:
        return redirect(url_for("inicio"))

    form = LoginForm()
    if form.validate_on_submit():
        usuario = services.autenticar(form.correo.data, form.clave.data)
        if usuario is None:
            flash("Correo o contraseña incorrectos.", "danger")
        else:
            login_user(usuario)
            return redirect(_destino_seguro(request.args.get("next")))

    return render_template("auth/login.html", form=form)


@bp.route("/registro", methods=["GET", "POST"])
def registro():
    """UI-02 Registro de cliente."""
    if current_user.is_authenticated:
        return redirect(url_for("inicio"))

    form = RegistroForm()
    if form.validate_on_submit():
        try:
            usuario, enlazada = services.registrar_cliente(
                nombres=form.nombres.data,
                apellidos=form.apellidos.data,
                cedula=form.cedula.data,
                correo=form.correo.data,
                clave=form.clave.data,
                telefono=form.telefono.data,
            )
        except services.RegistroRechazado as rechazo:
            getattr(form, rechazo.campo).errors.append(rechazo.mensaje)
        else:
            login_user(usuario)
            flash("¡Bienvenido! Tu cuenta quedó creada.", "success")
            if not enlazada:
                flash(
                    "Ya eras cliente de la tienda. Un vendedor enlazará tu cuenta cuando "
                    "verifique tu cédula en persona; mientras tanto no verás tus compras anteriores.",
                    "warning",
                )
            return redirect(url_for("inicio"))

    return render_template("auth/registro.html", form=form)


@bp.post("/logout")
def logout():
    logout_user()
    flash("Cerraste sesión.", "info")
    return redirect(url_for("auth.login"))


@bp.get("/")
@rol_requerido("administrador")
def index():
    return render_template(
        "en_construccion.html",
        modulo="Cuentas y acceso",
        historia="US-01",
        vistas="UI-13 (cuentas de vendedor)",
    )


def _destino_seguro(siguiente):
    """Después del login vuelve a la página que se pidió, pero solo si es de esta app."""
    if siguiente and siguiente.startswith("/") and not siguiente.startswith("//") and "\\" not in siguiente:
        return siguiente
    return url_for("inicio")
