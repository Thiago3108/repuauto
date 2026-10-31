"""Formularios del módulo Gestión de vehículos (US-03)."""
from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, Regexp

from app.validadores import limpiar


class VehiculoForm(FlaskForm):
    """UI-11: registrar o editar un vehículo.

    La marca se escribe libre (con sugerencias de las que ya existen): si es nueva,
    services.py la crea. El rango del año lo revisa services.py.
    """

    marca = StringField("Marca", filters=[limpiar], validators=[
        DataRequired("Escribe la marca del vehículo."),
        Length(max=60, message="Máximo 60 caracteres."),
    ])
    linea = StringField("Línea", filters=[limpiar], validators=[
        DataRequired("Escribe la línea del vehículo."),
        Length(max=60, message="Máximo 60 caracteres."),
    ])
    referencia = StringField("Referencia (opcional)", filters=[limpiar], validators=[
        Optional(),
        Length(max=60, message="Máximo 60 caracteres."),
    ])
    anio = StringField("Año (modelo)", filters=[limpiar], validators=[
        DataRequired("Escribe el año del vehículo."),
        Regexp(r"^[0-9]{4}$", message="El año debe tener 4 dígitos, por ejemplo 2018."),
    ])
    enviar = SubmitField("Guardar")


class CompatibilidadForm(FlaskForm):
    """UI-11: asociar un repuesto compatible a un vehículo (US-03 T3)."""

    id_repuesto = SelectField(
        "Repuesto compatible",
        coerce=int,
        validators=[DataRequired("Elige un repuesto.")],
    )
    enviar = SubmitField("Asociar repuesto")
