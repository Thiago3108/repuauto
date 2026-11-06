"""Formularios del módulo Proveedores y compras (US-09)."""
from flask_wtf import FlaskForm
from wtforms import DecimalField, FieldList, Form, FormField, IntegerField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, Regexp, ValidationError

from app.validadores import CORREO, SOLO_NUMEROS, limpiar

# Números, con el dígito de verificación opcional después de un guion: 900123456-7.
NIT = r"^[0-9]+(-[0-9])?$"


class ProveedorForm(FlaskForm):
    """Crear o editar un proveedor (UI-14)."""

    nit = StringField("NIT", filters=[limpiar], validators=[
        DataRequired("Escribe el NIT."),
        Length(max=20),
        Regexp(NIT, message="Usa solo números y, si tiene, el dígito de verificación con guion: 900123456-7."),
    ])
    nombre = StringField("Nombre", filters=[limpiar], validators=[
        DataRequired("Escribe el nombre del proveedor."),
        Length(max=100),
    ])
    telefono = StringField("Teléfono (opcional)", filters=[limpiar], validators=[
        Optional(),
        Length(max=20),
        Regexp(SOLO_NUMEROS, message="Usa solo números, sin espacios."),
    ])
    correo = StringField("Correo (opcional)", filters=[limpiar], validators=[
        Optional(),
        Length(max=120),
        Regexp(CORREO, message="Escribe un correo válido, por ejemplo ventas@proveedor.com."),
    ])
    enviar = SubmitField("Guardar")


class LineaCompraForm(Form):
    """Un repuesto de la compra. Es un Form simple: el token CSRF va en CompraForm.

    Si la línea tiene repuesto pero le falta la cantidad o el costo, lo avisa
    registrar_compra: Optional() detiene la validación cuando el campo viene vacío.
    """

    id_repuesto = SelectField("Repuesto", coerce=int, validate_choice=False, validators=[Optional()])
    cantidad = IntegerField("Cantidad", validators=[
        Optional(),
        NumberRange(min=1, message="La cantidad debe ser mayor que 0."),
    ])
    costo_unitario = DecimalField("Costo unitario", places=2, validators=[
        Optional(),
        NumberRange(min=0, message="El costo no puede ser negativo."),
    ])


class CompraForm(FlaskForm):
    """UI-14 Registro de compra a un proveedor."""

    id_proveedor = SelectField(
        "Proveedor", coerce=int, validate_choice=False,
        validators=[DataRequired("Elige el proveedor.")],
    )
    lineas = FieldList(FormField(LineaCompraForm), min_entries=1)
    enviar = SubmitField("Registrar compra")

    def poner_opciones(self, proveedores, repuestos):
        """Llena la lista de proveedores y la de repuestos de cada línea."""
        self.id_proveedor.choices = [(0, "Elige el proveedor")] + [
            (p.id_proveedor, f"{p.nombre} · NIT {p.nit}") for p in proveedores
        ]
        opciones = [(0, "Elige un repuesto")] + [
            (r.id_repuesto, f"{r.codigo} · {r.nombre} · stock {r.stock_actual}") for r in repuestos
        ]
        for linea in self.lineas:
            linea.id_repuesto.choices = opciones

    def lineas_elegidas(self):
        """Las líneas con repuesto, como (id_repuesto, cantidad, costo_unitario)."""
        return [
            (linea.id_repuesto.data, linea.cantidad.data, linea.costo_unitario.data)
            for linea in self.lineas
            if linea.id_repuesto.data
        ]

    def validate_lineas(self, campo):
        if not self.lineas_elegidas():
            raise ValidationError("Agrega al menos un repuesto a la compra.")
