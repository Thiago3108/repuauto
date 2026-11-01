"""Pruebas de US-07: reporte de ventas (T1) y acceso a la vista Reportes (UI-12)."""
from datetime import date, datetime
from decimal import Decimal

import pytest

from app.cli import estados_venta
from app.extensions import db
from app.models import Cliente, EstadoVenta, Venta
from app.reportes import services


@pytest.fixture()
def base_reporte(app, crear_cuenta):
    """Un vendedor, un cliente y los estados de flask seed."""
    estados_venta()
    vendedor = crear_cuenta("vendedor")
    cliente = Cliente(cedula="1098765432", nombres="Ana María", apellidos="Rueda Gómez")
    db.session.add(cliente)
    db.session.commit()
    return {"vendedor": vendedor, "cliente": cliente}


@pytest.fixture()
def venta(base_reporte):
    """Guarda una venta con la fecha, el total y el estado que se pidan."""

    def crear(fecha, total, estado="Completada"):
        nueva = Venta(
            cliente=base_reporte["cliente"],
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
