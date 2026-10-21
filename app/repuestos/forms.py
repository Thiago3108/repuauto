
"""Formularios para gestionar repuestos y existencias (US-04)."""

from decimal import Decimal

from flask_wtf import FlaskForm
from wtforms import (
    DecimalField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    InputRequired,
    Length,
    NumberRange,
    Optional,
)

from app.validadores import limpiar


class RepuestoForm(FlaskForm):
    """Formulario para crear o editar los datos generales de un repuesto."""

    codigo = StringField(
        "Código",
        filters=[limpiar],
        validators=[
            InputRequired(message="El código es obligatorio."),
            Length(max=30, message="El código no puede superar 30 caracteres."),
        ],
    )

    nombre = StringField(
        "Nombre",
        filters=[limpiar],
        validators=[
            InputRequired(message="El nombre es obligatorio."),
            Length(max=100, message="El nombre no puede superar 100 caracteres."),
        ],
    )

    descripcion = TextAreaField(
        "Descripción",
        filters=[limpiar],
        validators=[Optional()],
    )

    precio_venta = DecimalField(
        "Precio de venta",
        places=2,
        rounding=None,
        validators=[
            InputRequired(message="El precio es obligatorio."),
            NumberRange(
                min=Decimal("0"),
                message="El precio no puede ser negativo.",
            ),
        ],
    )

    id_categoria = SelectField(
        "Categoría",
        coerce=int,
        validators=[InputRequired(message="Selecciona una categoría.")],
    )

    id_marca_repuesto = SelectField(
        "Marca del repuesto",
        coerce=int,
        validators=[InputRequired(message="Selecciona una marca.")],
    )

    stock_minimo = IntegerField(
        "Stock mínimo",
        validators=[
            InputRequired(message="El stock mínimo es obligatorio."),
            NumberRange(min=0, message="El stock mínimo no puede ser negativo."),
        ],
    )

    submit = SubmitField("Guardar repuesto")


class CrearRepuestoForm(RepuestoForm):
    """Formulario de alta: permite indicar las existencias iniciales."""

    stock_actual = IntegerField(
        "Stock inicial",
        validators=[
            InputRequired(message="El stock inicial es obligatorio."),
            NumberRange(min=0, message="El stock inicial no puede ser negativo."),
        ],
    )

    submit = SubmitField("Crear repuesto")


class AjustarStockForm(FlaskForm):
    """Formulario para sumar o restar existencias."""

    cantidad = IntegerField(
        "Cantidad a ajustar (+ para agregar, - para retirar)",
        validators=[
            InputRequired(message="Indica una cantidad."),
            NumberRange(
                min=-2147483647,
                max=2147483647,
                message="La cantidad está fuera del rango permitido.",
            ),
        ],
    )

    motivo = StringField(
        "Motivo del ajuste",
        filters=[limpiar],
        validators=[
            InputRequired(message="El motivo es obligatorio."),
            Length(max=200, message="El motivo no puede superar 200 caracteres."),
        ],
    )

    submit = SubmitField("Ajustar stock")
