"""Pruebas de US-06: tablas de ventas."""
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.cli import estados_venta
from app.extensions import db
from app.models import Categoria, Cliente, DetalleVenta, EstadoVenta, MarcaRepuesto, Repuesto, Venta


@pytest.fixture()
def base_venta(app, crear_cuenta):
    """Un vendedor, un cliente, dos repuestos y los estados de flask seed."""
    estados_venta()
    vendedor = crear_cuenta("vendedor")
    cliente = Cliente(cedula="1098765432", nombres="Ana María", apellidos="Rueda Gómez")
    categoria = Categoria(nombre="Frenos")
    marca = MarcaRepuesto(nombre="Bosch")
    filtro = Repuesto(
        codigo="FIL-001", nombre="Filtro de aceite", precio_venta=Decimal("25000.00"),
        stock_actual=10, categoria=categoria, marca=marca,
    )
    pastillas = Repuesto(
        codigo="PAS-001", nombre="Pastillas de freno", precio_venta=Decimal("80000.00"),
        stock_actual=5, categoria=categoria, marca=marca,
    )
    db.session.add_all([cliente, filtro, pastillas])
    db.session.commit()
    return {"vendedor": vendedor, "cliente": cliente, "filtro": filtro, "pastillas": pastillas}


def estado(nombre):
    return db.session.scalar(db.select(EstadoVenta).filter_by(nombre=nombre))


def nueva_venta(base, metodo_pago="Efectivo", total=Decimal("0"), detalles=()):
    venta = Venta(
        cliente=base["cliente"], vendedor=base["vendedor"], estado=estado("Pendiente"),
        metodo_pago=metodo_pago, total=total, detalles=list(detalles),
    )
    db.session.add(venta)
    db.session.commit()
    return venta


def test_la_semilla_crea_los_tres_estados_sin_duplicar(app):
    estados_venta()
    estados_venta()
    db.session.commit()

    nombres = db.session.scalars(db.select(EstadoVenta.nombre).order_by(EstadoVenta.nombre)).all()
    assert nombres == ["Cancelada", "Completada", "Pendiente"]


def test_una_venta_guarda_cliente_vendedor_estado_y_detalles(base_venta):
    venta = nueva_venta(base_venta, total=Decimal("130000.00"), detalles=[
        DetalleVenta(repuesto=base_venta["filtro"], cantidad=2, precio_unitario=Decimal("25000.00")),
        DetalleVenta(repuesto=base_venta["pastillas"], cantidad=1, precio_unitario=Decimal("80000.00")),
    ])

    assert venta.fecha is not None
    assert venta.cliente.cedula == "1098765432"
    assert venta.vendedor.tiene_rol("vendedor")
    assert venta.estado.nombre == "Pendiente"
    assert [d.subtotal for d in venta.detalles] == [Decimal("50000.00"), Decimal("80000.00")]
    assert sum(d.subtotal for d in venta.detalles) == venta.total


def test_el_metodo_de_pago_debe_ser_uno_de_los_tres(base_venta):
    with pytest.raises(IntegrityError):
        nueva_venta(base_venta, metodo_pago="Cheque")


def test_el_total_no_puede_ser_negativo(base_venta):
    with pytest.raises(IntegrityError):
        nueva_venta(base_venta, total=Decimal("-1"))


def test_la_cantidad_debe_ser_mayor_que_cero(base_venta):
    with pytest.raises(IntegrityError):
        nueva_venta(base_venta, detalles=[
            DetalleVenta(repuesto=base_venta["filtro"], cantidad=0, precio_unitario=Decimal("25000.00")),
        ])


def test_el_precio_unitario_no_puede_ser_negativo(base_venta):
    with pytest.raises(IntegrityError):
        nueva_venta(base_venta, detalles=[
            DetalleVenta(repuesto=base_venta["filtro"], cantidad=1, precio_unitario=Decimal("-1")),
        ])


def test_un_repuesto_aparece_una_sola_vez_por_venta(base_venta):
    with pytest.raises(IntegrityError):
        nueva_venta(base_venta, detalles=[
            DetalleVenta(repuesto=base_venta["filtro"], cantidad=1, precio_unitario=Decimal("25000.00")),
            DetalleVenta(repuesto=base_venta["filtro"], cantidad=2, precio_unitario=Decimal("25000.00")),
        ])


def test_el_precio_del_detalle_no_cambia_si_sube_el_del_repuesto(base_venta):
    venta = nueva_venta(base_venta, total=Decimal("25000.00"), detalles=[
        DetalleVenta(repuesto=base_venta["filtro"], cantidad=1, precio_unitario=Decimal("25000.00")),
    ])

    base_venta["filtro"].precio_venta = Decimal("30000.00")
    db.session.commit()

    assert venta.detalles[0].precio_unitario == Decimal("25000.00")
