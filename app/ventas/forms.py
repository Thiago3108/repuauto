"""Formularios del módulo Ventas (US-06)."""
from flask_wtf import FlaskForm
from wtforms import FieldList, Form, FormField, IntegerField, RadioField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, Regexp, ValidationError

from app.models.venta import METODOS_DE_PAGO
from app.validadores import SOLO_NUMEROS, limpiar


class LineaVentaForm(Form):
    """Un repuesto de la venta. Es un Form simple: el token CSRF va en VentaForm."""

    id_repuesto = SelectField("Repuesto", coerce=int, validate_choice=False, validators=[Optional()])
    cantidad = IntegerField("Cantidad", validators=[
        Optional(),
        NumberRange(min=1, message="La cantidad debe ser mayor que 0."),
    ])

    def validate_cantidad(self, campo):
        if self.id_repuesto.data and campo.data is None:
            raise ValidationError("Escribe la cantidad.")


class VentaForm(FlaskForm):
    """UI-06 Registro de venta."""

    cedula = StringField("Cédula del cliente", filters=[limpiar], validators=[
        DataRequired("Escribe la cédula del cliente."),
        Length(max=20),
        Regexp(SOLO_NUMEROS, message="Usa solo números, sin puntos ni espacios."),
    ])
    lineas = FieldList(FormField(LineaVentaForm), min_entries=1)
    metodo_pago = SelectField(
        "Método de pago",
        choices=[("", "Elige el método de pago")] + [(m, m) for m in METODOS_DE_PAGO],
        validators=[DataRequired("Elige el método de pago.")],
    )
    estado = RadioField(
        "Estado",
        choices=[
            ("Completada", "Completada: el cliente pagó y se llevó el repuesto"),
            ("Pendiente", "Pendiente: el repuesto queda apartado"),
        ],
        default="Completada",
        validators=[DataRequired("Elige el estado de la venta.")],
    )
    enviar = SubmitField("Registrar venta")

    def poner_repuestos(self, repuestos):
        """Llena la lista de cada línea con los repuestos que se pueden vender."""
        opciones = [(0, "Elige un repuesto")] + [
            (r.id_repuesto, f"{r.codigo} · {r.nombre} · ${r.precio_venta:,.2f} · stock {r.stock_actual}")
            for r in repuestos
        ]
        for linea in self.lineas:
            linea.id_repuesto.choices = opciones

    def lineas_elegidas(self):
        """Las líneas con repuesto, como (id_repuesto, cantidad)."""
        return [
            (linea.id_repuesto.data, linea.cantidad.data)
            for linea in self.lineas
            if linea.id_repuesto.data
        ]

    def validate_lineas(self, campo):
        if not self.lineas_elegidas():
            raise ValidationError("Agrega al menos un repuesto a la venta.")
