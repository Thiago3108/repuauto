"""Pruebas de US-08: consultar estado de la venta e historial de compras (Mis compras, UI-05)."""
from datetime import datetime
from decimal import Decimal

import pytest

from app.cli import categorias_repuesto, estados_venta, marcas_repuesto
from app.extensions import db
from app.models import Categoria, Cliente, MarcaRepuesto, Repuesto
from app.ventas import services


@pytest.fixture()
def base_ventas(app, crear_cuenta):
    categorias_repuesto()
    marcas_repuesto()
    estados_venta()
    db.session.commit()
    return crear_cuenta("vendedor", correo="vendedor@repuauto.com")


def crear_repuesto(codigo="FRE-01", nombre="Pastillas de freno", precio="50000.00", stock=20):
    categoria = db.session.scalar(db.select(Categoria))
    marca = db.session.scalar(db.select(MarcaRepuesto))
    repuesto = Repuesto(
        codigo=codigo,
        nombre=nombre,
        precio_venta=Decimal(precio),
        stock_actual=stock,
        stock_minimo=2,
        id_categoria=categoria.id_categoria,
        id_marca_repuesto=marca.id_marca_repuesto,
    )
    db.session.add(repuesto)
    db.session.commit()
    return repuesto


def crear_cliente_enlazado(crear_cuenta, cedula="1098765432", correo="cliente1@repuauto.com", nombres="Carlos"):
    cuenta = crear_cuenta("cliente", correo=correo)
    cliente = Cliente(cedula=cedula, nombres=nombres, apellidos="Pérez", usuario=cuenta)
    db.session.add(cliente)
    db.session.commit()
    return cuenta, cliente


# ---------- Menú y control de acceso por rol ----------


def test_el_menu_del_cliente_muestra_mis_compras(client, crear_cuenta, iniciar_sesion):
    iniciar_sesion(crear_cuenta("cliente"))

    html = client.get("/").get_data(as_text=True)

    assert "Mis compras" in html
    assert "/ventas/mis-compras" in html


@pytest.mark.parametrize("rol", ["vendedor", "administrador"])
def test_solo_el_cliente_entra_a_mis_compras(client, crear_cuenta, iniciar_sesion, rol):
    iniciar_sesion(crear_cuenta(rol))

    assert client.get("/ventas/mis-compras").status_code == 403
    assert client.get("/ventas/mis-compras/1").status_code == 403


def test_mis_compras_sin_sesion_va_al_login(client):
    respuesta = client.get("/ventas/mis-compras")

    assert respuesta.status_code == 302
    assert "/auth/login" in respuesta.headers["Location"]


# ---------- Cuenta sin enlazar ----------


def test_si_la_cuenta_no_esta_enlazada_se_avisa_que_un_vendedor_debe_enlazarla(
    client, crear_cuenta, iniciar_sesion
):
    cuenta_sin_enlazar = crear_cuenta("cliente", correo="sin-enlace@repuauto.com")
    iniciar_sesion(cuenta_sin_enlazar)

    respuesta = client.get("/ventas/mis-compras")
    html = respuesta.get_data(as_text=True)

    assert respuesta.status_code == 200
    assert services.listar_compras_cliente(cuenta_sin_enlazar) == []
    assert "no está enlazada" in html
    assert "vendedor" in html


# ---------- Estado e historial de compras (T1, T2 y T3) ----------


def test_historial_muestra_compras_de_mas_reciente_a_mas_antigua_con_codigo_vta(
    client, crear_cuenta, iniciar_sesion, base_ventas
):
    cuenta, cliente = crear_cliente_enlazado(crear_cuenta)
    pastillas = crear_repuesto("FRE-01", "Pastillas de freno", "45000.00")
    filtro = crear_repuesto("FIL-02", "Filtro de aceite", "25000.00")

    primera = services.registrar_venta(
        cliente, base_ventas, [(pastillas.id_repuesto, 2)], "Efectivo", completada=True
    )
    primera.fecha = datetime(2026, 10, 1, 10, 0)

    segunda = services.registrar_venta(
        cliente, base_ventas, [(filtro.id_repuesto, 3)], "Tarjeta", completada=False
    )
    segunda.fecha = datetime(2026, 10, 15, 14, 30)
    db.session.commit()

    compras = services.listar_compras_cliente(cuenta)
    assert [v.id_venta for v in compras] == [segunda.id_venta, primera.id_venta]
    assert primera.codigo == f"#VTA-{primera.id_venta:04d}"
    assert primera.cantidad_productos == 2
    assert segunda.cantidad_productos == 3

    iniciar_sesion(cuenta)
    html = client.get("/ventas/mis-compras").get_data(as_text=True)

    assert primera.codigo in html
    assert segunda.codigo in html
    assert html.index(segunda.codigo) < html.index(primera.codigo)
    assert "90,000.00" in html
    assert "75,000.00" in html
    assert "Completada" in html
    assert "Pendiente" in html


def test_consultar_y_filtrar_el_estado_de_las_compras(
    client, crear_cuenta, iniciar_sesion, base_ventas
):
    cuenta, cliente = crear_cliente_enlazado(crear_cuenta)
    repuesto = crear_repuesto()

    pendiente = services.registrar_venta(
        cliente, base_ventas, [(repuesto.id_repuesto, 1)], "Efectivo", completada=False
    )
    completada = services.registrar_venta(
        cliente, base_ventas, [(repuesto.id_repuesto, 2)], "Transferencia", completada=True
    )

    assert [v.id_venta for v in services.listar_compras_cliente(cuenta, "Pendiente")] == [pendiente.id_venta]
    assert [v.id_venta for v in services.listar_compras_cliente(cuenta, "Completada")] == [completada.id_venta]

    iniciar_sesion(cuenta)
    html_pendientes = client.get("/ventas/mis-compras?estado=Pendiente").get_data(as_text=True)
    assert pendiente.codigo in html_pendientes
    assert completada.codigo not in html_pendientes

    services.cancelar_venta(pendiente.id_venta)
    html_detalle = client.get(f"/ventas/mis-compras/{pendiente.id_venta}").get_data(as_text=True)
    assert "Cancelada" in html_detalle
    assert "Esta compra fue cancelada." in html_detalle


def test_detalle_de_compra_funciona_con_id_y_con_codigo_vta(
    client, crear_cuenta, iniciar_sesion, base_ventas
):
    cuenta, cliente = crear_cliente_enlazado(crear_cuenta)
    repuesto = crear_repuesto("BUJ-09", "Bujía de iridio", "32000.00")
    venta = services.registrar_venta(
        cliente, base_ventas, [(repuesto.id_repuesto, 4)], "Tarjeta", completada=True
    )

    iniciar_sesion(cuenta)
    for ruta in (f"/ventas/mis-compras/{venta.id_venta}", f"/ventas/mis-compras/VTA-{venta.id_venta:04d}"):
        respuesta = client.get(ruta)
        html = respuesta.get_data(as_text=True)
        assert respuesta.status_code == 200
        assert venta.codigo in html
        assert "Bujía de iridio" in html
        assert "128,000.00" in html


# ---------- Seguridad entre clientes ----------


def test_un_cliente_nunca_ve_compras_de_otro_aunque_cambie_el_codigo_en_la_url(
    client, crear_cuenta, iniciar_sesion, base_ventas
):
    cuenta_ana, cliente_ana = crear_cliente_enlazado(
        crear_cuenta, cedula="11111111", correo="ana@repuauto.com", nombres="Ana"
    )
    cuenta_luis, _ = crear_cliente_enlazado(
        crear_cuenta, cedula="22222222", correo="luis@repuauto.com", nombres="Luis"
    )
    repuesto = crear_repuesto("ALT-99", "Alternador original", "480000.00")
    venta_de_ana = services.registrar_venta(
        cliente_ana, base_ventas, [(repuesto.id_repuesto, 1)], "Transferencia", completada=True
    )

    assert services.obtener_compra_cliente(cuenta_luis, venta_de_ana.id_venta) is None
    assert services.obtener_compra_cliente(cuenta_luis, venta_de_ana.codigo) is None

    iniciar_sesion(cuenta_luis)
    html_lista = client.get("/ventas/mis-compras").get_data(as_text=True)
    assert venta_de_ana.codigo not in html_lista
    assert "Todavía no tienes compras registradas." in html_lista

    for intento in (
        f"/ventas/mis-compras/{venta_de_ana.id_venta}",
        f"/ventas/mis-compras/VTA-{venta_de_ana.id_venta:04d}",
        f"/ventas/mis-compras/VTA-{venta_de_ana.id_venta}",
        "/ventas/mis-compras/9999",
        "/ventas/mis-compras/codigo-invalido",
    ):
        respuesta = client.get(intento)
        assert respuesta.status_code == 404
        assert "Alternador original" not in respuesta.get_data(as_text=True)
