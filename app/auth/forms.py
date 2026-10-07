"""Formularios del módulo Cuentas y acceso (US-01)."""
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Length


class LoginForm(FlaskForm):
    correo = StringField(
        "Correo", validators=[DataRequired("Escribe tu correo."), Length(max=120)]
    )
    clave = PasswordField("Contraseña", validators=[DataRequired("Escribe tu contraseña.")])
    enviar = SubmitField("Iniciar sesión")
