"""Formularios del módulo Gestión de clientes (US-02)."""
from flask_wtf import FlaskForm
from wtforms import BooleanField, HiddenField, StringField, SubmitField
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


class EnlazarCuentaForm(FlaskForm):
    """US-02 T4: el vendedor confirma que verificó la cédula antes de enlazar."""

    id_usuario = HiddenField(validators=[DataRequired("Elige la cuenta que vas a enlazar.")])
    verificado = BooleanField(
        "Verifiqué en persona que la cédula del cliente coincide",
        validators=[DataRequired("Confirma que verificaste la cédula en persona.")],
    )
    enviar = SubmitField("Enlazar esta cuenta")
