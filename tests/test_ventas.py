"""Pruebas de US-06: tablas de ventas, registrar venta con descuento de stock y UI-06."""
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.cli import estados_venta
from app.extensions import db
from app.models import Categoria, Cliente, DetalleVenta, EstadoVenta, MarcaRepuesto, Repuesto, Venta
from app.ventas import services


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


# ---------- Registrar venta y descontar stock (US-06 T2 y T3) ----------


def registrar(base, lineas, metodo_pago="Efectivo", completada=True):
    return services.registrar_venta(base["cliente"], base["vendedor"], lineas, metodo_pago, completada)


def test_registrar_venta_copia_precios_calcula_total_y_descuenta_stock(base_venta):
    filtro, pastillas = base_venta["filtro"], base_venta["pastillas"]

    venta = registrar(base_venta, [(filtro.id_repuesto, 2), (pastillas.id_repuesto, 1)], "Tarjeta")

    assert venta.estado.nombre == "Completada"
    assert venta.metodo_pago == "Tarjeta"
    assert venta.vendedor is base_venta["vendedor"]
    assert venta.total == Decimal("130000.00")
    assert {d.repuesto.codigo: d.precio_unitario for d in venta.detalles} == {
        "FIL-001": Decimal("25000.00"), "PAS-001": Decimal("80000.00"),
    }
    assert (filtro.stock_actual, pastillas.stock_actual) == (8, 4)


def test_una_venta_pendiente_tambien_aparta_el_stock(base_venta):
    venta = registrar(base_venta, [(base_venta["filtro"].id_repuesto, 3)], completada=False)

    assert venta.estado.nombre == "Pendiente"
    assert base_venta["filtro"].stock_actual == 7


def test_si_un_repuesto_se_repite_se_suman_las_cantidades(base_venta):
    filtro = base_venta["filtro"]

    venta = registrar(base_venta, [(filtro.id_repuesto, 1), (filtro.id_repuesto, 2)])

    assert [(d.repuesto.codigo, d.cantidad) for d in venta.detalles] == [("FIL-001", 3)]
    assert filtro.stock_actual == 7


def test_sin_stock_suficiente_no_se_guarda_nada_y_dice_cual_falta(base_venta):
    filtro, pastillas = base_venta["filtro"], base_venta["pastillas"]

    with pytest.raises(services.VentaRechazada) as rechazo:
        registrar(base_venta, [(filtro.id_repuesto, 2), (pastillas.id_repuesto, 6)])

    assert "Pastillas de freno (quedan 5)" in rechazo.value.mensaje
    assert "Filtro" not in rechazo.value.mensaje
    assert db.session.scalar(db.select(db.func.count(Venta.id_venta))) == 0
    assert db.session.scalar(db.select(db.func.count(DetalleVenta.id_detalle_venta))) == 0
    assert (db.session.get(Repuesto, filtro.id_repuesto).stock_actual,
            db.session.get(Repuesto, pastillas.id_repuesto).stock_actual) == (10, 5)


def test_se_puede_vender_todo_el_stock(base_venta):
    registrar(base_venta, [(base_venta["pastillas"].id_repuesto, 5)])

    assert base_venta["pastillas"].stock_actual == 0


@pytest.mark.parametrize("lineas, metodo_pago, mensaje", [
    ([], "Efectivo", "al menos un repuesto"),
    ([("filtro", 0)], "Efectivo", "mayor que 0"),
    ([("filtro", 1)], "Cheque", "método de pago"),
])
def test_rechaza_ventas_incompletas(base_venta, lineas, metodo_pago, mensaje):
    lineas = [(base_venta[nombre].id_repuesto, cantidad) for nombre, cantidad in lineas]

    with pytest.raises(services.VentaRechazada, match=mensaje):
        registrar(base_venta, lineas, metodo_pago)
    assert base_venta["filtro"].stock_actual == 10


def test_rechaza_venta_sin_cliente(base_venta):
    with pytest.raises(services.VentaRechazada, match="cliente"):
        services.registrar_venta(None, base_venta["vendedor"], [(base_venta["filtro"].id_repuesto, 1)], "Efectivo")


def test_rechaza_un_repuesto_desactivado(base_venta):
    base_venta["filtro"].activo = False
    db.session.commit()

    with pytest.raises(services.VentaRechazada, match="desactivado"):
        registrar(base_venta, [(base_venta["filtro"].id_repuesto, 1)])
    assert db.session.get(Repuesto, base_venta["filtro"].id_repuesto).stock_actual == 10


# ---------- Vista "Registro de venta" (UI-06) ----------


def datos_venta(base, lineas=(("filtro", "2"),), **cambios):
    datos = {"cedula": base["cliente"].cedula, "metodo_pago": "Efectivo", "estado": "Completada"}
    for i, (nombre, cantidad) in enumerate(lineas):
        datos[f"lineas-{i}-id_repuesto"] = str(base[nombre].id_repuesto)
        datos[f"lineas-{i}-cantidad"] = cantidad
    datos.update(cambios)
    return datos


def test_el_vendedor_registra_una_venta_desde_la_pantalla(client, base_venta, iniciar_sesion):
    iniciar_sesion(base_venta["vendedor"])

    respuesta = client.post("/ventas/nueva", data=datos_venta(
        base_venta, lineas=(("filtro", "2"), ("pastillas", "1")),
    ), follow_redirects=True)

    html = respuesta.get_data(as_text=True)
    assert "Se registró la venta" in html
    assert "$130,000.00" in html
    assert "Ana María Rueda Gómez" in html
    assert base_venta["filtro"].stock_actual == 8


def test_la_pantalla_avisa_si_falta_stock(client, base_venta, iniciar_sesion):
    iniciar_sesion(base_venta["vendedor"])

    respuesta = client.post("/ventas/nueva", data=datos_venta(base_venta, lineas=(("pastillas", "9"),)))

    assert "No hay stock suficiente de: Pastillas de freno (quedan 5)." in respuesta.get_data(as_text=True)
    assert db.session.scalar(db.select(db.func.count(Venta.id_venta))) == 0


def test_la_pantalla_avisa_si_la_cedula_no_es_de_un_cliente(client, base_venta, iniciar_sesion):
    iniciar_sesion(base_venta["vendedor"])

    respuesta = client.post("/ventas/nueva", data=datos_venta(base_venta, cedula="999"))

    html = respuesta.get_data(as_text=True)
    assert "No hay un cliente con esta cédula" in html
    assert "Regístralo aquí" in html


def test_la_pantalla_pide_al_menos_un_repuesto(client, base_venta, iniciar_sesion):
    iniciar_sesion(base_venta["vendedor"])

    respuesta = client.post("/ventas/nueva", data=datos_venta(base_venta, lineas=()))

    assert "Agrega al menos un repuesto a la venta." in respuesta.get_data(as_text=True)


def test_la_lista_y_el_detalle_muestran_la_venta(client, base_venta, iniciar_sesion):
    venta = registrar(base_venta, [(base_venta["filtro"].id_repuesto, 1)], completada=False)
    iniciar_sesion(base_venta["vendedor"])

    lista = client.get("/ventas/").get_data(as_text=True)
    detalle = client.get(f"/ventas/{venta.id_venta}").get_data(as_text=True)

    assert "Pendiente" in lista and "$25,000.00" in lista
    assert "FIL-001" in detalle and "Pendiente" in detalle
    assert client.get("/ventas/9999").status_code == 404


def test_un_cliente_no_puede_registrar_ventas(client, crear_cuenta, iniciar_sesion):
    iniciar_sesion(crear_cuenta("cliente"))

    assert client.get("/ventas/nueva").status_code == 403


# ---------- Completar o cancelar ventas (US-06 T4, UI-07) ----------


def stock(repuesto):
    return db.session.get(Repuesto, repuesto.id_repuesto).stock_actual


def test_completar_una_venta_pendiente_no_cambia_el_stock(base_venta):
    venta = registrar(base_venta, [(base_venta["filtro"].id_repuesto, 2)], completada=False)

    services.completar_venta(venta.id_venta)

    assert venta.estado.nombre == "Completada"
    assert stock(base_venta["filtro"]) == 8


def test_solo_se_completan_las_ventas_pendientes(base_venta):
    venta = registrar(base_venta, [(base_venta["filtro"].id_repuesto, 1)])

    with pytest.raises(services.VentaRechazada, match="Solo se completan las ventas pendientes"):
        services.completar_venta(venta.id_venta)


@pytest.mark.parametrize("completada", [False, True])
def test_cancelar_una_venta_devuelve_el_stock(base_venta, completada):
    filtro, pastillas = base_venta["filtro"], base_venta["pastillas"]
    venta = registrar(base_venta, [(filtro.id_repuesto, 2), (pastillas.id_repuesto, 5)], completada=completada)

    services.cancelar_venta(venta.id_venta)

    assert venta.estado.nombre == "Cancelada"
    assert (stock(filtro), stock(pastillas)) == (10, 5)
    assert len(venta.detalles) == 2


def test_una_venta_cancelada_no_devuelve_el_stock_dos_veces(base_venta):
    venta = registrar(base_venta, [(base_venta["filtro"].id_repuesto, 3)])
    services.cancelar_venta(venta.id_venta)

    with pytest.raises(services.VentaRechazada, match="ya estaba cancelada"):
        services.cancelar_venta(venta.id_venta)
    with pytest.raises(services.VentaRechazada):
        services.completar_venta(venta.id_venta)
    assert stock(base_venta["filtro"]) == 10


def test_cambiar_el_estado_de_una_venta_que_no_existe(app):
    assert services.completar_venta(9999) is None
    assert services.cancelar_venta(9999) is None


def test_la_lista_filtra_por_estado(client, base_venta, iniciar_sesion):
    pendiente = registrar(base_venta, [(base_venta["filtro"].id_repuesto, 1)], completada=False)
    completada = registrar(base_venta, [(base_venta["pastillas"].id_repuesto, 1)])
    iniciar_sesion(base_venta["vendedor"])

    html = client.get("/ventas/?estado=Pendiente").get_data(as_text=True)

    assert f'href="/ventas/{pendiente.id_venta}"' in html
    assert f'href="/ventas/{completada.id_venta}"' not in html
    assert "No hay ventas canceladas." in client.get("/ventas/?estado=Cancelada").get_data(as_text=True)


def test_completar_y_cancelar_desde_la_pantalla(client, base_venta, iniciar_sesion):
    venta = registrar(base_venta, [(base_venta["filtro"].id_repuesto, 4)], completada=False)
    iniciar_sesion(base_venta["vendedor"])

    respuesta = client.post(f"/ventas/{venta.id_venta}/completar", data={"volver": "/ventas/?estado=Pendiente"})
    assert respuesta.headers["Location"] == "/ventas/?estado=Pendiente"

    respuesta = client.post(f"/ventas/{venta.id_venta}/cancelar", follow_redirects=True)
    html = respuesta.get_data(as_text=True)
    assert f"Se canceló la venta #{venta.id_venta} y se devolvió el stock." in html
    assert stock(base_venta["filtro"]) == 10

    respuesta = client.post(f"/ventas/{venta.id_venta}/cancelar", follow_redirects=True)
    assert "Esta venta ya estaba cancelada." in respuesta.get_data(as_text=True)
    assert stock(base_venta["filtro"]) == 10


def test_no_redirige_fuera_de_ventas(client, base_venta, iniciar_sesion):
    venta = registrar(base_venta, [(base_venta["filtro"].id_repuesto, 1)], completada=False)
    iniciar_sesion(base_venta["vendedor"])

    respuesta = client.post(f"/ventas/{venta.id_venta}/completar", data={"volver": "https://otro-sitio.com"})

    assert respuesta.headers["Location"] == f"/ventas/{venta.id_venta}"


def test_cambiar_el_estado_pide_ser_del_personal(client, base_venta, crear_cuenta, iniciar_sesion):
    venta = registrar(base_venta, [(base_venta["filtro"].id_repuesto, 1)], completada=False)
    iniciar_sesion(crear_cuenta("cliente"))

    assert client.post(f"/ventas/{venta.id_venta}/cancelar").status_code == 403
    assert client.post("/ventas/9999/completar").status_code == 403
    assert stock(base_venta["filtro"]) == 9
