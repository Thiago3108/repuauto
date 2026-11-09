"""Pruebas de US-07: reportes de ventas (T1), inventario (T2) y clientes (T3), compras y
resumen de ventas y compras, y la vista Reportes (UI-12, T4) con sus gráficos."""
from datetime import date, datetime
from decimal import Decimal

import pytest

from app.cli import estados_venta
from app.extensions import db
from app.models import Categoria, Cliente, Compra, EstadoVenta, MarcaRepuesto, Proveedor, Repuesto, Venta
from app.reportes import services


@pytest.fixture()
def base_reporte(app, crear_cuenta):
    """Un vendedor, un cliente registrado antes de los rangos de las pruebas y los estados
    de flask seed."""
    estados_venta()
    vendedor = crear_cuenta("vendedor")
    cliente = Cliente(
        cedula="1098765432", nombres="Ana María", apellidos="Rueda Gómez", creado_en=datetime(2025, 1, 1),
    )
    db.session.add(cliente)
    db.session.commit()
    return {"vendedor": vendedor, "cliente": cliente}


@pytest.fixture()
def venta(base_reporte):
    """Guarda una venta con la fecha, el total y el estado que se pidan. Sin cliente, es
    del cliente de base_reporte."""

    def crear(fecha, total, estado="Completada", cliente=None):
        nueva = Venta(
            cliente=cliente or base_reporte["cliente"],
            vendedor=base_reporte["vendedor"],
            estado=db.session.scalar(db.select(EstadoVenta).filter_by(nombre=estado)),
            metodo_pago="Efectivo",
            total=Decimal(total),
            fecha=fecha,
        )
        db.session.add(nueva)
        db.session.commit()
        return nueva

    return crear


@pytest.fixture()
def nuevo_cliente(base_reporte):
    """Guarda un cliente registrado en la fecha que se pida."""

    def crear(cedula, nombres, creado_en):
        cliente = Cliente(cedula=cedula, nombres=nombres, apellidos="Prueba", creado_en=creado_en)
        db.session.add(cliente)
        db.session.commit()
        return cliente

    return crear


@pytest.fixture()
def compra(app, crear_cuenta):
    """Guarda una compra con la fecha y el total que se pidan. Sin proveedor, es de uno de
    prueba (NIT 900111222-3)."""
    administrador = crear_cuenta("administrador", correo="compras@repuauto.com")
    por_defecto = []

    def crear(fecha, total, proveedor=None):
        if proveedor is None:
            if not por_defecto:
                por_defecto.append(Proveedor(nit="900111222-3", nombre="Proveedor de prueba"))
            proveedor = por_defecto[0]
        nueva = Compra(proveedor=proveedor, usuario=administrador, total=Decimal(total), fecha=fecha)
        db.session.add(nueva)
        db.session.commit()
        return nueva

    return crear


# ---------- Rango de fechas ----------


def test_sin_fechas_el_rango_es_el_mes_actual_hasta_hoy():
    assert services.rango_de_fechas("", "", hoy=date(2026, 11, 20)) == (date(2026, 11, 1), date(2026, 11, 20))


def test_el_rango_toma_las_fechas_escritas():
    assert services.rango_de_fechas("2026-09-01", "2026-10-31") == (date(2026, 9, 1), date(2026, 10, 31))


@pytest.mark.parametrize("desde, hasta", [("2026-13-01", ""), ("ayer", "2026-10-01")])
def test_una_fecha_mal_escrita_se_rechaza(desde, hasta):
    with pytest.raises(services.RangoInvalido):
        services.rango_de_fechas(desde, hasta)


def test_la_fecha_inicial_no_puede_ir_despues_de_la_final():
    with pytest.raises(services.RangoInvalido):
        services.rango_de_fechas("2026-10-31", "2026-10-01")


# ---------- Reporte de ventas ----------


def test_solo_cuentan_las_ventas_completadas(venta):
    venta(datetime(2026, 10, 5, 10, 0), "100000.00")
    venta(datetime(2026, 10, 6, 10, 0), "50000.00", estado="Pendiente")
    venta(datetime(2026, 10, 7, 10, 0), "70000.00", estado="Cancelada")

    reporte = services.reporte_ventas(date(2026, 10, 1), date(2026, 10, 31))

    assert reporte["ventas"] == 1
    assert reporte["total"] == Decimal("100000.00")


def test_las_dos_fechas_del_rango_se_incluyen_completas(venta):
    venta(datetime(2026, 9, 30, 23, 59), "1000.00")
    venta(datetime(2026, 10, 1, 0, 0), "2000.00")
    venta(datetime(2026, 10, 31, 23, 59), "3000.00")
    venta(datetime(2026, 11, 1, 0, 0), "4000.00")

    reporte = services.reporte_ventas(date(2026, 10, 1), date(2026, 10, 31))

    assert reporte["ventas"] == 2
    assert reporte["total"] == Decimal("5000.00")


def test_el_reporte_agrupa_por_mes_e_incluye_los_meses_sin_ventas(venta):
    venta(datetime(2026, 8, 10, 9, 0), "10000.00")
    venta(datetime(2026, 8, 20, 9, 0), "15000.00")
    venta(datetime(2026, 10, 3, 9, 0), "30000.00")

    reporte = services.reporte_ventas(date(2026, 8, 1), date(2026, 10, 31))

    assert [(m["nombre"], m["ventas"], m["total"]) for m in reporte["meses"]] == [
        ("Agosto 2026", 2, Decimal("25000.00")),
        ("Septiembre 2026", 0, Decimal("0")),
        ("Octubre 2026", 1, Decimal("30000.00")),
    ]
    assert reporte["ventas"] == 3
    assert reporte["total"] == Decimal("55000.00")
    assert reporte["promedio"] == Decimal("18333.33")


def test_el_rango_puede_cruzar_de_un_anio_a_otro(venta):
    venta(datetime(2026, 12, 15, 9, 0), "10000.00")
    venta(datetime(2027, 1, 15, 9, 0), "20000.00")

    reporte = services.reporte_ventas(date(2026, 12, 1), date(2027, 1, 31))

    assert [m["nombre"] for m in reporte["meses"]] == ["Diciembre 2026", "Enero 2027"]
    assert reporte["total"] == Decimal("30000.00")


def test_sin_ventas_el_reporte_da_cero(base_reporte):
    reporte = services.reporte_ventas(date(2026, 10, 1), date(2026, 10, 31))

    assert reporte["ventas"] == 0
    assert reporte["total"] == Decimal("0")
    assert reporte["promedio"] == Decimal("0")


# ---------- Reporte de clientes ----------


def test_los_clientes_nuevos_se_cuentan_por_mes_dentro_del_rango(nuevo_cliente):
    nuevo_cliente("1001", "Antes", datetime(2026, 7, 31, 23, 59))
    nuevo_cliente("1002", "Agosto", datetime(2026, 8, 1, 0, 0))
    nuevo_cliente("1003", "Agosto dos", datetime(2026, 8, 25, 18, 0))
    nuevo_cliente("1004", "Octubre", datetime(2026, 10, 31, 23, 59))
    nuevo_cliente("1005", "Despues", datetime(2026, 11, 1, 0, 0))

    reporte = services.reporte_clientes(date(2026, 8, 1), date(2026, 10, 31))

    assert [(m["nombre"], m["nuevos"]) for m in reporte["meses"]] == [
        ("Agosto 2026", 2), ("Septiembre 2026", 0), ("Octubre 2026", 1),
    ]
    assert reporte["nuevos"] == 3


def test_los_que_mas_compran_se_ordenan_por_total_y_solo_cuentan_completadas(
    venta, nuevo_cliente, base_reporte
):
    ana = base_reporte["cliente"]
    luis = nuevo_cliente("2001", "Luis", datetime(2025, 1, 1))
    eva = nuevo_cliente("2002", "Eva", datetime(2025, 1, 1))
    venta(datetime(2026, 10, 2, 9, 0), "30000.00", cliente=ana)
    venta(datetime(2026, 10, 9, 9, 0), "40000.00", cliente=ana)
    venta(datetime(2026, 10, 5, 9, 0), "100000.00", cliente=luis)
    venta(datetime(2026, 10, 6, 9, 0), "900000.00", estado="Pendiente", cliente=eva)
    venta(datetime(2026, 10, 7, 9, 0), "800000.00", estado="Cancelada", cliente=eva)
    venta(datetime(2026, 9, 30, 9, 0), "500000.00", cliente=eva)

    mejores = services.reporte_clientes(date(2026, 10, 1), date(2026, 10, 31))["mejores"]

    assert [(m["cliente"].nombres, m["compras"], m["total"]) for m in mejores] == [
        ("Luis", 1, Decimal("100000.00")),
        ("Ana María", 2, Decimal("70000.00")),
    ]


def test_si_empatan_en_total_va_primero_el_que_mas_compras_hizo(venta, nuevo_cliente, base_reporte):
    beto = nuevo_cliente("3001", "Beto", datetime(2025, 1, 1))
    venta(datetime(2026, 10, 2, 9, 0), "50000.00", cliente=beto)
    venta(datetime(2026, 10, 3, 9, 0), "25000.00", cliente=base_reporte["cliente"])
    venta(datetime(2026, 10, 4, 9, 0), "25000.00", cliente=base_reporte["cliente"])

    mejores = services.reporte_clientes(date(2026, 10, 1), date(2026, 10, 31))["mejores"]

    assert [m["cliente"].nombres for m in mejores] == ["Ana María", "Beto"]


def test_los_que_mas_compran_se_limitan(venta, nuevo_cliente):
    for numero in range(12):
        cliente = nuevo_cliente(f"40{numero:02d}", f"Cliente {numero:02d}", datetime(2025, 1, 1))
        venta(datetime(2026, 10, 2, 9, 0), f"{1000 * (numero + 1)}.00", cliente=cliente)

    mejores = services.reporte_clientes(date(2026, 10, 1), date(2026, 10, 31))["mejores"]

    assert len(mejores) == 10
    assert mejores[0]["cliente"].nombres == "Cliente 11"
    assert len(services.reporte_clientes(date(2026, 10, 1), date(2026, 10, 31), limite=3)["mejores"]) == 3


def test_sin_clientes_ni_compras_el_reporte_queda_vacio(base_reporte):
    reporte = services.reporte_clientes(date(2026, 10, 1), date(2026, 10, 31))

    assert reporte["nuevos"] == 0
    assert reporte["mejores"] == []


# ---------- Reporte de inventario ----------


@pytest.fixture()
def repuesto(app):
    """Guarda un repuesto en la categoría que se pida (la crea si no existe)."""
    marca = MarcaRepuesto(nombre="Bosch")
    categorias = {}

    def crear(codigo, categoria, stock, minimo=0, precio="1000.00", activo=True):
        if categoria not in categorias:
            categorias[categoria] = Categoria(nombre=categoria)
        nuevo = Repuesto(
            codigo=codigo, nombre=f"Repuesto {codigo}", precio_venta=Decimal(precio),
            stock_actual=stock, stock_minimo=minimo, activo=activo,
            categoria=categorias[categoria], marca=marca,
        )
        db.session.add(nuevo)
        db.session.commit()
        return nuevo

    return crear


def test_el_inventario_cuenta_repuestos_por_categoria_y_estado_del_stock(repuesto):
    repuesto("F-1", "Frenos", stock=10, minimo=3, precio="2000.00")
    repuesto("F-2", "Frenos", stock=2, minimo=3, precio="5000.00")
    repuesto("F-3", "Frenos", stock=0, minimo=3)
    repuesto("A-1", "Aceites", stock=0)
    repuesto("A-2", "Aceites", stock=4, minimo=4, precio="500.00")

    reporte = services.reporte_inventario()

    assert [c["nombre"] for c in reporte["categorias"]] == ["Aceites", "Frenos"]
    aceites, frenos = reporte["categorias"]
    assert frenos["estados"] == {"En stock": 1, "Stock bajo": 1, "Agotado": 1}
    assert (frenos["repuestos"], frenos["unidades"], frenos["valor"]) == (3, 12, Decimal("30000.00"))
    assert aceites["estados"] == {"En stock": 1, "Stock bajo": 0, "Agotado": 1}
    assert reporte["estados"] == {"En stock": 2, "Stock bajo": 1, "Agotado": 2}
    assert (reporte["repuestos"], reporte["unidades"], reporte["valor"]) == (5, 16, Decimal("32000.00"))


def test_los_repuestos_desactivados_no_entran_al_inventario(repuesto):
    repuesto("F-1", "Frenos", stock=5)
    repuesto("F-2", "Frenos", stock=0, activo=False)
    repuesto("L-1", "Luces", stock=9, activo=False)

    reporte = services.reporte_inventario()

    assert [c["nombre"] for c in reporte["categorias"]] == ["Frenos"]
    assert reporte["repuestos"] == 1
    assert reporte["por_reponer"] == []


def test_por_reponer_trae_agotados_y_stock_bajo_primero_los_que_menos_tienen(repuesto):
    repuesto("OK", "Frenos", stock=8, minimo=2)
    bajo = repuesto("BAJO", "Frenos", stock=1, minimo=5)
    agotado = repuesto("CERO", "Aceites", stock=0)

    assert services.reporte_inventario()["por_reponer"] == [agotado, bajo]


def test_sin_repuestos_el_inventario_queda_vacio(app):
    reporte = services.reporte_inventario()

    assert reporte["categorias"] == []
    assert reporte["repuestos"] == 0
    assert reporte["valor"] == Decimal("0")


# ---------- Reporte de compras ----------


def test_las_compras_se_agrupan_por_mes_con_los_meses_sin_compras(compra):
    compra(datetime(2026, 8, 3, 9, 0), "100000.00")
    compra(datetime(2026, 8, 25, 9, 0), "50000.00")
    compra(datetime(2026, 10, 1, 0, 0), "20000.00")

    reporte = services.reporte_compras(date(2026, 8, 1), date(2026, 10, 31))

    assert reporte["compras"] == 3
    assert reporte["total"] == Decimal("170000.00")
    assert [(m["nombre"], m["compras"], m["total"]) for m in reporte["meses"]] == [
        ("Agosto 2026", 2, Decimal("150000.00")),
        ("Septiembre 2026", 0, Decimal("0")),
        ("Octubre 2026", 1, Decimal("20000.00")),
    ]


def test_las_compras_fuera_del_rango_no_cuentan(compra):
    compra(datetime(2026, 9, 30, 23, 59), "1000.00")
    compra(datetime(2026, 10, 15, 12, 0), "2000.00")
    compra(datetime(2026, 11, 1, 0, 0), "4000.00")

    reporte = services.reporte_compras(date(2026, 10, 1), date(2026, 10, 31))

    assert reporte["compras"] == 1
    assert reporte["total"] == Decimal("2000.00")


def test_los_proveedores_se_ordenan_por_lo_comprado_y_se_limitan(compra):
    andina = Proveedor(nit="800000001-1", nombre="Andina")
    boreal = Proveedor(nit="800000002-2", nombre="Boreal")
    compra(datetime(2026, 10, 2, 9, 0), "30000.00", proveedor=andina)
    compra(datetime(2026, 10, 3, 9, 0), "30000.00", proveedor=andina)
    compra(datetime(2026, 10, 4, 9, 0), "90000.00", proveedor=boreal)
    compra(datetime(2026, 10, 5, 9, 0), "10000.00")

    reporte = services.reporte_compras(date(2026, 10, 1), date(2026, 10, 31), limite=2)

    assert [(f["proveedor"].nombre, f["compras"], f["total"]) for f in reporte["proveedores"]] == [
        ("Boreal", 1, Decimal("90000.00")),
        ("Andina", 2, Decimal("60000.00")),
    ]


def test_sin_compras_el_reporte_da_cero(app):
    reporte = services.reporte_compras(date(2026, 10, 1), date(2026, 10, 31))

    assert reporte["compras"] == 0
    assert reporte["total"] == Decimal("0")
    assert reporte["proveedores"] == []


# ---------- Resumen de ventas y compras ----------


def test_el_resumen_resta_lo_comprado_de_lo_vendido_mes_por_mes(venta, compra):
    venta(datetime(2026, 9, 10, 9, 0), "100000.00")
    venta(datetime(2026, 10, 10, 9, 0), "40000.00")
    venta(datetime(2026, 10, 11, 9, 0), "999999.00", estado="Cancelada")
    compra(datetime(2026, 10, 2, 9, 0), "70000.00")
    desde, hasta = date(2026, 9, 1), date(2026, 10, 31)

    resumen = services.reporte_consolidado(
        services.reporte_ventas(desde, hasta), services.reporte_compras(desde, hasta)
    )

    assert resumen["vendido"] == Decimal("140000.00")
    assert resumen["comprado"] == Decimal("70000.00")
    assert resumen["diferencia"] == Decimal("70000.00")
    assert [(m["nombre"], m["vendido"], m["comprado"], m["diferencia"]) for m in resumen["meses"]] == [
        ("Septiembre 2026", Decimal("100000.00"), Decimal("0"), Decimal("100000.00")),
        ("Octubre 2026", Decimal("40000.00"), Decimal("70000.00"), Decimal("-30000.00")),
    ]


# ---------- Vista Reportes (UI-12) ----------


@pytest.mark.parametrize("rol", ["cliente", "vendedor"])
def test_solo_el_administrador_entra_a_reportes(client, crear_cuenta, iniciar_sesion, rol):
    iniciar_sesion(crear_cuenta(rol))
    assert client.get("/reportes/").status_code == 403


def test_reportes_sin_sesion_va_al_login(client):
    assert client.get("/reportes/").status_code == 302


def test_la_vista_muestra_el_total_y_los_meses_del_rango(
    client, crear_cuenta, iniciar_sesion, venta
):
    venta(datetime(2026, 9, 10, 9, 0), "25000.00")
    venta(datetime(2026, 10, 10, 9, 0), "1234567.50")
    iniciar_sesion(crear_cuenta("administrador"))

    html = client.get("/reportes/?desde=2026-09-01&hasta=2026-10-31").get_data(as_text=True)

    assert "$1,259,567.50" in html
    assert "Septiembre 2026" in html
    assert "Octubre 2026" in html


def test_con_fechas_invalidas_la_vista_avisa_y_muestra_el_mes_actual(
    client, crear_cuenta, iniciar_sesion
):
    iniciar_sesion(crear_cuenta("administrador"))

    respuesta = client.get("/reportes/?desde=2026-10-31&hasta=2026-10-01")

    assert respuesta.status_code == 200
    assert "La fecha inicial no puede ir después de la fecha final." in respuesta.get_data(as_text=True)


def test_la_vista_muestra_los_clientes_nuevos_y_los_que_mas_compran(
    client, crear_cuenta, iniciar_sesion, venta, nuevo_cliente
):
    luis = nuevo_cliente("5001", "Luis", datetime(2026, 10, 3, 9, 0))
    venta(datetime(2026, 10, 10, 9, 0), "345000.00", cliente=luis)
    iniciar_sesion(crear_cuenta("administrador"))

    html = client.get("/reportes/?desde=2026-10-01&hasta=2026-10-31").get_data(as_text=True)

    assert "Clientes nuevos" in html
    assert "Luis Prueba" in html
    assert f"/clientes/{luis.id_cliente}" in html
    assert "$345,000.00" in html


def test_la_vista_muestra_el_inventario_y_los_repuestos_por_reponer(
    client, crear_cuenta, iniciar_sesion, repuesto
):
    repuesto("F-1", "Frenos", stock=10, precio="1500.00")
    agotado = repuesto("F-2", "Frenos", stock=0)
    iniciar_sesion(crear_cuenta("administrador"))

    html = client.get("/reportes/").get_data(as_text=True)

    assert 'id="inventario"' in html
    assert "$15,000.00" in html
    assert "Repuesto F-2" in html
    assert f"/repuestos/{agotado.id_repuesto}/ajustar-stock" in html


def test_la_vista_tiene_todas_las_secciones(client, crear_cuenta, iniciar_sesion):
    iniciar_sesion(crear_cuenta("administrador"))

    html = client.get("/reportes/").get_data(as_text=True)

    for seccion in ("resumen", "ventas", "compras", "clientes", "inventario"):
        assert f'href="#{seccion}"' in html
        assert f'id="{seccion}"' in html


def test_la_vista_muestra_las_compras_y_el_resumen(client, crear_cuenta, iniciar_sesion, venta, compra):
    venta(datetime(2026, 10, 10, 9, 0), "100000.00")
    compra(datetime(2026, 10, 2, 9, 0), "130000.00", proveedor=Proveedor(nit="800000003-3", nombre="Autopartes Cali"))
    iniciar_sesion(crear_cuenta("administrador"))

    html = client.get("/reportes/?desde=2026-10-01&hasta=2026-10-31").get_data(as_text=True)

    assert "Autopartes Cali" in html
    assert "$130,000.00" in html
    assert "-$30,000.00" in html


def test_la_vista_dibuja_los_graficos_con_los_datos_del_rango(
    client, crear_cuenta, iniciar_sesion, venta, compra, nuevo_cliente, repuesto
):
    venta(datetime(2026, 9, 10, 9, 0), "25000.50")
    compra(datetime(2026, 10, 2, 9, 0), "130000.00")
    nuevo_cliente("5002", "Marta", datetime(2026, 10, 3, 9, 0))
    repuesto("F-1", "Frenos", stock=0)
    iniciar_sesion(crear_cuenta("administrador"))

    html = client.get("/reportes/?desde=2026-09-01&hasta=2026-10-31").get_data(as_text=True)

    assert "chart.js@4.4.1" in html
    for grafico in ("resumen", "ventas", "proveedores", "clientes", "inventario"):
        assert f'id="grafico-{grafico}"' in html
    assert 'id="datos-graficos"' in html
    assert '"vendido": [25000.5, 0.0]' in html
    assert '"comprado": [0.0, 130000.0]' in html
    assert '"clientes": [0, 1]' in html


def test_sin_datos_la_vista_no_dibuja_graficos(client, crear_cuenta, iniciar_sesion):
    iniciar_sesion(crear_cuenta("administrador"))

    html = client.get("/reportes/?desde=2026-09-01&hasta=2026-10-31").get_data(as_text=True)

    assert "<canvas" not in html
    assert "No hay ventas completadas ni compras en este rango de fechas." in html
