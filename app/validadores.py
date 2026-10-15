"""Reglas de formato compartidas por los formularios de todos los módulos.

Uso: from app.validadores import SOLO_LETRAS, SOLO_NUMEROS, CORREO, limpiar
"""
SOLO_LETRAS = r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]+$"
SOLO_NUMEROS = r"^[0-9]+$"
# Revisión sencilla del formato: algo@algo.algo, sin espacios.
CORREO = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


def limpiar(valor):
    """Filtro de WTForms: quita los espacios de los extremos y deja uno solo entre palabras."""
    return " ".join(valor.split()) if valor else valor
