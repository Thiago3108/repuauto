"""Extensiones de Flask, creadas sin app.

Se crean aquí y se conectan a la app dentro de create_app(). Si vivieran en
app/__init__.py, los modelos tendrían que importar de app y app de los modelos:
una importación circular.
"""
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from sqlalchemy import MetaData

# Nombres fijos para índices, únicos, llaves foráneas y primarias. Sin esto, PostgreSQL
# inventa nombres distintos en cada computador y las migraciones que los modifican fallan.
# Las restricciones CHECK no están aquí porque se nombran a mano, como en el DBML (chk_...).
CONVENCION_DE_NOMBRES = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

db = SQLAlchemy(metadata=MetaData(naming_convention=CONVENCION_DE_NOMBRES))
migrate = Migrate()
csrf = CSRFProtect()

# Sesiones de usuario (US-01). Quien no ha iniciado sesión y abre una página protegida
# termina en la pantalla de iniciar sesión (UI-01).
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Inicia sesión para continuar."
login_manager.login_message_category = "warning"
