"""Fábrica de la aplicación RepuAuto.

create_app() construye la app en lugar de dejarla como variable global. Así se puede
crear una con la configuración normal y otra con la de pruebas sin tocar código.
Es el "controlador principal" del patrón MVC: recibe la petición y la reparte a
los blueprints de cada módulo.
"""
from datetime import date

from flask import Flask, render_template
from flask_login import current_user

from app.extensions import csrf, db, login_manager, migrate
from app.menu import menu_para
from app.reportes.services import MESES
from config import Config

DIAS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")

VARIABLES_REQUERIDAS = {
    "SECRET_KEY": "SECRET_KEY",
    "SQLALCHEMY_DATABASE_URI": "DATABASE_URL (o TEST_DATABASE_URL en pruebas)",
}


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    _validar_configuracion(app)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)

    # Importa los modelos para que Flask-Migrate los vea al generar migraciones.
    from app import models  # noqa: F401

    from app.auth import bp as auth_bp
    from app.clientes import bp as clientes_bp
    from app.vehiculos import bp as vehiculos_bp
    from app.repuestos import bp as repuestos_bp
    from app.catalogo import bp as catalogo_bp
    from app.ventas import bp as ventas_bp
    from app.reportes import bp as reportes_bp
    from app.compras import bp as compras_bp
    from app.api import bp as api_bp
    from app.consolidado import bp as consolidado_bp

    blueprints = (
        auth_bp, clientes_bp, vehiculos_bp, repuestos_bp,
        catalogo_bp, ventas_bp, reportes_bp, compras_bp, api_bp, consolidado_bp,
    )
    for blueprint in blueprints:
        app.register_blueprint(blueprint)

    from app.cli import cambiar_clave_command, crear_admin_command, seed_command

    for comando in (seed_command, crear_admin_command, cambiar_clave_command):
        app.cli.add_command(comando)

    @app.context_processor
    def menu_lateral():
        return {"menu": menu_para(current_user)}

    @app.errorhandler(403)
    def sin_permiso(error):
        return render_template("errores/403.html"), 403

    @app.get("/")
    def inicio():
        from app.resumen import resumen_para

        hoy = date.today()
        fecha = f"{DIAS[hoy.weekday()]}, {hoy.day} de {MESES[hoy.month - 1].lower()} de {hoy.year}"
        return render_template("inicio.html", resumen=resumen_para(current_user, hoy), fecha=fecha)

    return app


def _validar_configuracion(app):
    faltantes = [variable for clave, variable in VARIABLES_REQUERIDAS.items() if not app.config.get(clave)]
    if faltantes:
        raise RuntimeError(
            "Faltan variables en tu .env: " + ", ".join(faltantes)
            + ". Copia .env.example como .env y complétalo."
        )
