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

    # API REST para la integración entre sedes (opcionales en el .env).
    API_SUCURSAL = os.environ.get("API_SUCURSAL", "Bucaramanga")
    API_IVA = int(os.environ.get("API_IVA", "19"))  # porcentaje, incluido en los precios
    API_TOKEN_HORAS = float(os.environ.get("API_TOKEN_HORAS", "8"))

    # La otra sede, para el informe consolidado (opcionales en el .env). Ver docs/API.md.
    SEDE_REMOTA_NOMBRE = os.environ.get("SEDE_REMOTA_NOMBRE", "Sede UD1")
    SEDE_REMOTA_URL = os.environ.get("SEDE_REMOTA_URL", "")
    SEDE_REMOTA_TIPO = os.environ.get("SEDE_REMOTA_TIPO", "repuauto")
    SEDE_REMOTA_USUARIO = os.environ.get("SEDE_REMOTA_USUARIO", "")
    SEDE_REMOTA_CLAVE = os.environ.get("SEDE_REMOTA_CLAVE", "")


class TestConfig(Config):
    """Configuración de pruebas: usa otra base de datos que se puede borrar sin miedo."""

    TESTING = True
    SECRET_KEY = os.environ.get("SECRET_KEY", "clave-de-pruebas")
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL")
    # Las pruebas envían formularios sin el token CSRF que pondría el navegador.
    WTF_CSRF_ENABLED = False
    # Las pruebas nunca se conectan a la otra sede de verdad, aunque el .env la tenga.
    SEDE_REMOTA_URL = ""
