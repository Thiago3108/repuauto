"""Formularios del módulo Cuentas y acceso (US-01)."""
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length, Optional, Regexp, ValidationError

from app.auth.services import contrasena_segura

SOLO_LETRAS = r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]+$"
SOLO_NUMEROS = r"^[0-9]+$"
# Revisión sencilla del formato: algo@algo.algo, sin espacios.
CORREO = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


def limpiar(valor):
    """Quita los espacios de los extremos y deja uno solo entre palabras."""
    return " ".join(valor.split()) if valor else valor


class LoginForm(FlaskForm):
    correo = StringField(
        "Correo", validators=[DataRequired("Escribe tu correo."), Length(max=120)]
    )
    clave = PasswordField("Contraseña", validators=[DataRequired("Escribe tu contraseña.")])
    enviar = SubmitField("Iniciar sesión")


class RegistroForm(FlaskForm):
    """UI-02 Registro de cliente."""

    nombres = StringField("Nombres", filters=[limpiar], validators=[
        DataRequired("Escribe tus nombres."),
        Length(max=60),
        Regexp(SOLO_LETRAS, message="Usa solo letras y espacios."),
    ])
    apellidos = StringField("Apellidos", filters=[limpiar], validators=[
        DataRequired("Escribe tus apellidos."),
        Length(max=60),
        Regexp(SOLO_LETRAS, message="Usa solo letras y espacios."),
    ])
    cedula = StringField("Cédula", filters=[limpiar], validators=[
        DataRequired("Escribe tu cédula."),
        Length(max=20),
        Regexp(SOLO_NUMEROS, message="Usa solo números, sin puntos ni espacios."),
    ])
    telefono = StringField("Teléfono (opcional)", filters=[limpiar], validators=[
        Optional(),
        Length(max=20),
        Regexp(SOLO_NUMEROS, message="Usa solo números, sin espacios."),
    ])
    correo = StringField("Correo", filters=[limpiar], validators=[
        DataRequired("Escribe tu correo."),
        Length(max=120),
        Regexp(CORREO, message="Escribe un correo válido, por ejemplo nombre@correo.com."),
    ])
    clave = PasswordField("Contraseña", validators=[DataRequired("Escribe una contraseña.")])
    confirmar = PasswordField("Repite la contraseña", validators=[
        DataRequired("Repite la contraseña."),
        EqualTo("clave", message="Las contraseñas no coinciden."),
    ])
    enviar = SubmitField("Crear cuenta")

    def validate_clave(self, campo):
        if not contrasena_segura(campo.data):
            raise ValidationError(
                "Debe tener más de 8 caracteres, al menos un número y un carácter especial."
            )
