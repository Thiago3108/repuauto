"""Fábrica de la aplicación RepuAuto.

create_app() construye la app en lugar de dejarla como variable global. Así se puede
crear una con la configuración normal y otra con la de pruebas sin tocar código.
Es el "controlador principal" del patrón MVC: recibe la petición y la reparte a
los blueprints de cada módulo.
"""
from flask import Flask, render_template

from app.extensions import csrf, db, migrate
from app.menu import MENU
from config import Config

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

    blueprints = (
        auth_bp, clientes_bp, vehiculos_bp, repuestos_bp,
        catalogo_bp, ventas_bp, reportes_bp, compras_bp,
    )
    for blueprint in blueprints:
        app.register_blueprint(blueprint)

    from app.cli import seed_command

    app.cli.add_command(seed_command)

    @app.context_processor
    def menu_lateral():
        return {"menu": MENU}

    @app.get("/")
    def inicio():
        return render_template("inicio.html")

    return app


def _validar_configuracion(app):
    faltantes = [variable for clave, variable in VARIABLES_REQUERIDAS.items() if not app.config.get(clave)]
    if faltantes:
        raise RuntimeError(
            "Faltan variables en tu .env: " + ", ".join(faltantes)
            + ". Copia .env.example como .env y complétalo."
        )
