
"""Pruebas de los servicios de repuestos y stock (US-04)."""

from decimal import Decimal

import pytest

from app.extensions import db
from app.models import Categoria, MarcaRepuesto
from app.repuestos import services


@pytest.fixture
def catalogo_base(app):
    """Prepara una categoría y una marca para las pruebas."""
    categoria = Categoria(nombre="Motor")
    marca = MarcaRepuesto(nombre="Bosch")

    db.session.add_all([categoria, marca])
    db.session.flush()

    return {
        "categoria": categoria,
        "marca": marca,
    }


def crear_repuesto_prueba(catalogo_base, **cambios):
    """Crea un repuesto con valores válidos por defecto."""
    datos = {
        "codigo": "REP-001",
        "nombre": "Filtro de aceite",
        "precio_venta": Decimal("25000.00"),
        "id_categoria": catalogo_base["categoria"].id_categoria,
        "id_marca_repuesto": catalogo_base["marca"].id_marca_repuesto,
        "descripcion": "Filtro para motor",
        "stock_actual": 10,
        "stock_minimo": 3,
    }
    datos.update(cambios)
    return services.crear_repuesto(**datos)


def test_crear_repuesto_correctamente(app, catalogo_base):
    repuesto = crear_repuesto_prueba(catalogo_base)

    assert repuesto.id_repuesto is not None
    assert repuesto.codigo == "REP-001"
    assert repuesto.nombre == "Filtro de aceite"
    assert repuesto.precio_venta == Decimal("25000.00")
    assert repuesto.stock_actual == 10
    assert repuesto.activo is True


def test_rechaza_codigo_duplicado(app, catalogo_base):
    crear_repuesto_prueba(catalogo_base)

    with pytest.raises(services.ErrorRepuesto, match="Ya existe"):
        crear_repuesto_prueba(catalogo_base)


def test_rechaza_precio_negativo(app, catalogo_base):
    with pytest.raises(services.ErrorRepuesto, match="precio"):
        crear_repuesto_prueba(
            catalogo_base,
            precio_venta=Decimal("-100.00"),
        )


def test_rechaza_stock_inicial_negativo(app, catalogo_base):
    with pytest.raises(services.ErrorRepuesto, match="stock"):
        crear_repuesto_prueba(catalogo_base, stock_actual=-1)


def test_rechaza_ajuste_que_deja_stock_negativo(app, catalogo_base):
    repuesto = crear_repuesto_prueba(
        catalogo_base,
        stock_actual=2,
    )

    with pytest.raises(services.ErrorRepuesto, match="existencias suficientes"):
        services.ajustar_stock(repuesto, -3)

    db.session.refresh(repuesto)
    assert repuesto.stock_actual == 2


def test_ajustar_stock_correctamente(app, catalogo_base):
    repuesto = crear_repuesto_prueba(
        catalogo_base,
        stock_actual=5,
    )

    services.ajustar_stock(repuesto, 4, motivo="Reposición")

    db.session.refresh(repuesto)
    assert repuesto.stock_actual == 9


def test_rechaza_ajuste_de_cero(app, catalogo_base):
    repuesto = crear_repuesto_prueba(catalogo_base)

    with pytest.raises(services.ErrorRepuesto, match="diferente de cero"):
        services.ajustar_stock(repuesto, 0)


def test_lista_repuestos_con_stock_bajo(app, catalogo_base):
    repuesto = crear_repuesto_prueba(
        catalogo_base,
        stock_actual=1,
        stock_minimo=3,
    )

    alertas = services.listar_stock_bajo()

    assert repuesto in alertas


def test_desactivar_repuesto(app, catalogo_base):
    repuesto = crear_repuesto_prueba(catalogo_base)

    services.desactivar_repuesto(repuesto)

    db.session.refresh(repuesto)
    assert repuesto.activo is False
    assert repuesto in services.listar_repuestos(incluir_inactivos=True)
    assert repuesto not in services.listar_repuestos()
