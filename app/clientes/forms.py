"""Formularios del módulo Gestión de clientes (US-02)."""
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, Regexp

from app.validadores import SOLO_LETRAS, SOLO_NUMEROS, limpiar


class ClienteForm(FlaskForm):
    """Crear o editar un cliente (UI-08)."""

    cedula = StringField("Cédula", filters=[limpiar], validators=[
        DataRequired("Escribe la cédula."),
        Length(max=20),
        Regexp(SOLO_NUMEROS, message="Usa solo números, sin puntos ni espacios."),
    ])
    nombres = StringField("Nombres", filters=[limpiar], validators=[
        DataRequired("Escribe los nombres."),
        Length(max=60),
        Regexp(SOLO_LETRAS, message="Usa solo letras y espacios."),
    ])
    apellidos = StringField("Apellidos", filters=[limpiar], validators=[
        DataRequired("Escribe los apellidos."),
        Length(max=60),
        Regexp(SOLO_LETRAS, message="Usa solo letras y espacios."),
    ])
    telefono = StringField("Teléfono (opcional)", filters=[limpiar], validators=[
        Optional(),
        Length(max=20),
        Regexp(SOLO_NUMEROS, message="Usa solo números, sin espacios."),
    ])
    enviar = SubmitField("Guardar")
