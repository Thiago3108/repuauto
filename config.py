"""Configuración de RepuAuto.

Los valores sensibles (claves, conexión a la base de datos) no van en el código:
se leen del archivo .env de cada integrante. Así el código es el mismo en los cuatro
computadores y cada uno pone sus propias claves.
"""
import os

from dotenv import load_dotenv

# Carga el .env también cuando no se usa el comando flask (por ejemplo, con pytest).
load_dotenv()


class Config:
    """Configuración normal de desarrollo."""

    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")


class TestConfig(Config):
    """Configuración de pruebas: usa otra base de datos que se puede borrar sin miedo."""

    TESTING = True
    SECRET_KEY = os.environ.get("SECRET_KEY", "clave-de-pruebas")
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL")
    # Las pruebas envían formularios sin el token CSRF que pondría el navegador.
    WTF_CSRF_ENABLED = False
