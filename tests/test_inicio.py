"""Pruebas de la página de inicio (cifras del día según el rol) y de la estructura de la
interfaz: menú con iconos, portada de acceso y hoja de estilos."""
from datetime import date, datetime
from decimal import Decimal

import pytest

from app.cli import estados_venta
from app.extensions import db
from app.menu import MENU
from app.models import Categoria, Cliente, EstadoVenta, MarcaRepuesto, Repuesto, Venta
from app.resumen import resumen_para

HOY = date(2026, 11, 10)


@pytest.fixture()
def datos(app, crear_cuenta):
    """Ventas de hoy, de ayer y de otro mes en varios estados, y repuestos en cada estado
    del stock. La cuenta de cliente queda enlazada al cliente de las ventas."""
    estados_venta()
    vendedor = crear_cuenta("vendedor")
    cuenta = crear_cuenta("cliente")
    estados = {e.nombre: e for e in db.session.scalars(db.select(EstadoVenta))}
    cliente = Cliente(cedula="1098000001", nombres="Carlos", apellidos="Rueda", usuario=cuenta)

    def venta(fecha, total, estado="Completada"):
        return Venta(cliente=cliente, vendedor=vendedor, estado=estados[estado], metodo_pago="Efectivo",
                     total=Decimal(total), fecha=fecha)

    categoria, marca = Categoria(nombre="Frenos"), MarcaRepuesto(nombre="Bosch")

    def repuesto(codigo, stock, minimo, activo=True):
        return Repuesto(codigo=codigo, nombre=codigo, categoria=categoria, marca=marca, stock_actual=stock,
                        stock_minimo=minimo, precio_venta=Decimal("1000.00"), activo=activo)

    db.session.add_all([
        venta(datetime(2026, 11, 10, 9, 0), "100000.00"),
        venta(datetime(2026, 11, 10, 23, 59), "50000.00"),
        venta(datetime(2026, 11, 10, 10, 0), "999000.00", estado="Cancelada"),
        venta(datetime(2026, 11, 9, 10, 0), "30000.00"),
        venta(datetime(2026, 11, 8, 10, 0), "70000.00", estado="Pendiente"),
        venta(datetime(2026, 10, 31, 23, 59), "500000.00"),
        repuesto("OK", 10, 4), repuesto("BAJO", 2, 4), repuesto("AGOTADO-1", 0, 4), repuesto("AGOTADO-2", 0, 0),
        repuesto("INACTIVO", 0, 4, activo=False),
    ])
    db.session.commit()
    return {"vendedor": vendedor, "cliente": cuenta}


def por_titulo(tarjetas):
    return {t["titulo"]: t for t in tarjetas}


# ---------- Cifras ----------


def test_el_vendedor_ve_las_ventas_de_hoy_las_pendientes_y_lo_que_hay_que_reponer(app, datos):
    with app.test_request_context():
        tarjetas = por_titulo(resumen_para(datos["vendedor"], HOY))

    assert list(tarjetas) == ["Ventas de hoy", "Ventas pendientes", "Repuestos por reponer"]
    assert (tarjetas["Ventas de hoy"]["valor"], tarjetas["Ventas de hoy"]["detalle"]) == ("$150,000", "2 ventas completadas")
    assert (tarjetas["Ventas pendientes"]["valor"], tarjetas["Ventas pendientes"]["detalle"]) == ("1", "$70,000 por entregar")
    assert tarjetas["Repuestos por reponer"]["valor"] == "3"
    assert tarjetas["Repuestos por reponer"]["detalle"] == "2 agotados · 1 con stock bajo"
    assert tarjetas["Repuestos por reponer"]["color"] == "rojo"


def test_el_administrador_ve_ademas_lo_vendido_en_el_mes(app, datos, crear_cuenta):
    with app.test_request_context():
        tarjetas = por_titulo(resumen_para(crear_cuenta("administrador"), HOY))

    assert tarjetas["Vendido este mes"]["valor"] == "$180,000"
    assert tarjetas["Vendido este mes"]["detalle"] == "3 ventas"
    assert tarjetas["Vendido este mes"]["enlace"] == "/reportes/"


def test_el_cliente_ve_sus_compras_y_las_que_tiene_por_recoger(app, datos):
    with app.test_request_context():
        tarjetas = por_titulo(resumen_para(datos["cliente"], HOY))

    assert list(tarjetas) == ["Mis compras", "Por recoger"]
    assert (tarjetas["Mis compras"]["valor"], tarjetas["Mis compras"]["detalle"]) == ("4", "$680,000 en total")
    assert tarjetas["Por recoger"]["valor"] == "1"


def test_una_cuenta_de_cliente_sin_enlazar_no_tiene_cifras(app, crear_cuenta):
    with app.test_request_context():
        assert resumen_para(crear_cuenta("cliente"), HOY) == []


def test_sin_datos_las_cifras_quedan_en_cero(app, crear_cuenta):
    estados_venta()
    with app.test_request_context():
        tarjetas = por_titulo(resumen_para(crear_cuenta("vendedor"), HOY))

    assert tarjetas["Ventas de hoy"]["valor"] == "$0"
    assert tarjetas["Ventas pendientes"]["detalle"] == "Todo entregado"
    assert tarjetas["Repuestos por reponer"]["detalle"] == "Inventario al día"


# ---------- Página de inicio y estructura ----------


def test_el_inicio_muestra_las_cifras_y_los_accesos_del_rol(client, datos, iniciar_sesion):
    iniciar_sesion(datos["vendedor"])

    html = client.get("/").get_data(as_text=True)

    assert "Ventas pendientes" in html and "Repuestos por reponer" in html
    assert "Vendido este mes" not in html
    assert "Registra ventas y completa o cancela las pendientes." in html
    assert 'href="/ventas/?estado=Pendiente"' in html


def test_cada_entrada_del_menu_tiene_icono_y_descripcion():
    for item in MENU:
        assert item["icono"] and item["descripcion"].endswith(".")


def test_el_menu_lateral_marca_el_modulo_actual_y_lleva_iconos(client, crear_cuenta, iniciar_sesion):
    iniciar_sesion(crear_cuenta("administrador"))

    html = client.get("/reportes/").get_data(as_text=True)

    assert 'id="menu-lateral"' in html
    assert '<i class="bi bi-bar-chart-line" aria-hidden="true"></i>Reportes' in html
    assert html.count('class="nav-link active"') == 2  # el del menú lateral y la pestaña Consolidado
    assert 'aria-label="Cerrar sesión"' in html


def test_sin_sesion_se_ve_la_portada_y_no_el_menu(client):
    html = client.get("/auth/login").get_data(as_text=True)

    assert "ra-portada" in html
    assert "Tu vehículo en" in html
    assert 'id="menu-lateral"' not in html


def test_la_hoja_de_estilos_se_sirve_sin_iniciar_sesion(client):
    respuesta = client.get("/static/css/app.css")

    assert respuesta.status_code == 200
    assert "--ra-azul" in respuesta.get_data(as_text=True)
