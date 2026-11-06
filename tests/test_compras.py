"""Pruebas de US-09: tablas de compras (T1), proveedores (T2), registrar compra y sumar al
stock (T3) y la vista Proveedores y compras (UI-14, T4)."""
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.compras import services
from app.extensions import db
from app.models import Categoria, Compra, DetalleCompra, MarcaRepuesto, Proveedor, Repuesto


@pytest.fixture()
def base_compra(app, crear_cuenta):
    """Un administrador, un proveedor y dos repuestos."""
    administrador = crear_cuenta("administrador")
    proveedor = Proveedor(nit="900123456-7", nombre="Distribuidora Andina", telefono="6071234567")
    categoria = Categoria(nombre="Frenos")
    marca = MarcaRepuesto(nombre="Bosch")
    filtro = Repuesto(
        codigo="FIL-001", nombre="Filtro de aceite", precio_venta=Decimal("25000.00"),
        stock_actual=2, categoria=categoria, marca=marca,
    )
    pastillas = Repuesto(
        codigo="PAS-001", nombre="Pastillas de freno", precio_venta=Decimal("80000.00"),
        stock_actual=0, categoria=categoria, marca=marca,
    )
    db.session.add_all([proveedor, filtro, pastillas])
    db.session.commit()
    return {"administrador": administrador, "proveedor": proveedor, "filtro": filtro, "pastillas": pastillas}


def contar(modelo):
    return db.session.scalar(db.select(db.func.count()).select_from(modelo))


# ---------- Tablas (T1) ----------


def test_una_compra_guarda_proveedor_administrador_y_detalles(base_compra):
    compra = Compra(
        proveedor=base_compra["proveedor"], usuario=base_compra["administrador"], total=Decimal("36000.00"),
        detalles=[DetalleCompra(repuesto=base_compra["filtro"], cantidad=3, costo_unitario=Decimal("12000.00"))],
    )
    db.session.add(compra)
    db.session.commit()

    assert compra.fecha is not None
    assert compra.proveedor.nit == "900123456-7"
    assert compra.usuario.tiene_rol("administrador")
    assert compra.detalles[0].subtotal == Decimal("36000.00")


def test_el_nit_del_proveedor_no_se_repite(base_compra):
    db.session.add(Proveedor(nit="900123456-7", nombre="Otro"))
    with pytest.raises(IntegrityError):
        db.session.commit()


@pytest.mark.parametrize("cantidad, costo", [(0, "1000.00"), (2, "-1.00")])
def test_la_cantidad_debe_ser_positiva_y_el_costo_no_negativo(base_compra, cantidad, costo):
    compra = Compra(
        proveedor=base_compra["proveedor"], usuario=base_compra["administrador"], total=Decimal("0"),
        detalles=[DetalleCompra(repuesto=base_compra["filtro"], cantidad=cantidad, costo_unitario=Decimal(costo))],
    )
    db.session.add(compra)
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_el_total_de_la_compra_no_puede_ser_negativo(base_compra):
    db.session.add(Compra(proveedor=base_compra["proveedor"], usuario=base_compra["administrador"], total=Decimal("-1")))
    with pytest.raises(IntegrityError):
        db.session.commit()


# ---------- Proveedores (T2) ----------


def test_crear_y_editar_un_proveedor(app):
    proveedor = services.crear_proveedor("800111222", "Autopartes del Norte", "", "ventas@norte.com")
    assert (proveedor.telefono, proveedor.correo) == (None, "ventas@norte.com")

    services.actualizar_proveedor(proveedor, "800111222-3", "Autopartes del Norte SAS", "3001234567", "")

    assert db.session.get(Proveedor, proveedor.id_proveedor).nit == "800111222-3"
    assert proveedor.telefono == "3001234567"
    assert proveedor.correo is None


def test_no_se_crea_un_proveedor_con_un_nit_que_ya_existe(base_compra):
    with pytest.raises(services.NitRepetido) as repetido:
        services.crear_proveedor("900123456-7", "Copia")

    assert repetido.value.existente.nombre == "Distribuidora Andina"
    assert contar(Proveedor) == 1


def test_no_se_edita_un_proveedor_con_el_nit_de_otro(base_compra):
    otro = services.crear_proveedor("800111222", "Autopartes del Norte")

    with pytest.raises(services.NitRepetido):
        services.actualizar_proveedor(otro, "900123456-7", "Autopartes del Norte")


def test_se_puede_guardar_un_proveedor_sin_cambiar_su_nit(base_compra):
    proveedor = base_compra["proveedor"]
    services.actualizar_proveedor(proveedor, proveedor.nit, "Distribuidora Andina SAS")

    assert proveedor.nombre == "Distribuidora Andina SAS"


def test_buscar_proveedores_por_nit_o_nombre(base_compra):
    services.crear_proveedor("800111222", "Autopartes del Norte")

    assert [p.nombre for p in services.listar_proveedores("norte")] == ["Autopartes del Norte"]
    assert [p.nombre for p in services.listar_proveedores("900123")] == ["Distribuidora Andina"]
    assert len(services.listar_proveedores()) == 2
    assert services.listar_proveedores("100%") == []


# ---------- Registrar compra y sumar al stock (T3) ----------


def test_registrar_una_compra_suma_al_stock_y_calcula_el_total(base_compra):
    filtro, pastillas = base_compra["filtro"], base_compra["pastillas"]

    compra = services.registrar_compra(base_compra["proveedor"], base_compra["administrador"], [
        (filtro.id_repuesto, 10, Decimal("12000")),
        (pastillas.id_repuesto, 4, Decimal("50000.50")),
    ])

    assert (filtro.stock_actual, pastillas.stock_actual) == (12, 4)
    assert compra.total == Decimal("320002.00")
    assert compra.usuario == base_compra["administrador"]
    assert sorted(d.cantidad for d in compra.detalles) == [4, 10]


def test_un_repuesto_repetido_con_el_mismo_costo_se_suma_en_una_linea(base_compra):
    filtro = base_compra["filtro"]

    compra = services.registrar_compra(base_compra["proveedor"], base_compra["administrador"], [
        (filtro.id_repuesto, 3, Decimal("1000")), (filtro.id_repuesto, 2, Decimal("1000.00")),
    ])

    assert [(d.cantidad, d.costo_unitario) for d in compra.detalles] == [(5, Decimal("1000.00"))]
    assert filtro.stock_actual == 7


@pytest.mark.parametrize("lineas, mensaje", [
    ([], "Agrega al menos un repuesto"),
    ([("filtro", 0, "1000")], "cantidad mayor que 0"),
    ([("filtro", 2, "-1")], "no puede ser negativo"),
    ([("filtro", 2, None)], "Escribe el costo"),
    ([("filtro", 2, "1000"), ("filtro", 1, "900")], "costos distintos"),
])
def test_una_compra_invalida_no_guarda_nada_ni_cambia_el_stock(base_compra, lineas, mensaje):
    lineas = [
        (base_compra[r].id_repuesto, cantidad, None if costo is None else Decimal(costo))
        for r, cantidad, costo in lineas
    ]

    with pytest.raises(services.CompraRechazada, match=mensaje):
        services.registrar_compra(base_compra["proveedor"], base_compra["administrador"], lineas)

    assert contar(Compra) == 0
    assert base_compra["filtro"].stock_actual == 2


def test_si_un_repuesto_esta_desactivado_no_se_guarda_nada(base_compra):
    filtro, pastillas = base_compra["filtro"], base_compra["pastillas"]
    pastillas.activo = False
    db.session.commit()

    with pytest.raises(services.CompraRechazada, match="desactivado"):
        services.registrar_compra(base_compra["proveedor"], base_compra["administrador"], [
            (filtro.id_repuesto, 5, Decimal("1000")), (pastillas.id_repuesto, 5, Decimal("1000")),
        ])

    db.session.expire_all()
    assert contar(Compra) == 0
    assert db.session.get(Repuesto, filtro.id_repuesto).stock_actual == 2


def test_la_compra_exige_proveedor_y_un_administrador(base_compra, crear_cuenta):
    linea = [(base_compra["filtro"].id_repuesto, 1, Decimal("1000"))]

    with pytest.raises(services.CompraRechazada, match="proveedor"):
        services.registrar_compra(None, base_compra["administrador"], linea)
    with pytest.raises(services.CompraRechazada, match="administrador"):
        services.registrar_compra(base_compra["proveedor"], crear_cuenta("vendedor"), linea)
    assert contar(Compra) == 0


# ---------- Vista Proveedores y compras (UI-14) ----------


RUTAS = ["/compras/", "/compras/nueva", "/compras/proveedores", "/compras/proveedores/nuevo"]


@pytest.mark.parametrize("rol", ["cliente", "vendedor"])
@pytest.mark.parametrize("ruta", RUTAS)
def test_solo_el_administrador_entra_a_compras(client, crear_cuenta, iniciar_sesion, rol, ruta):
    iniciar_sesion(crear_cuenta(rol))
    assert client.get(ruta).status_code == 403


def test_compras_sin_sesion_va_al_login(client):
    assert client.get("/compras/").status_code == 302


def test_la_pantalla_registra_un_proveedor(client, crear_cuenta, iniciar_sesion):
    iniciar_sesion(crear_cuenta("administrador"))

    respuesta = client.post("/compras/proveedores/nuevo", data={
        "nit": " 800111222-3 ", "nombre": "Autopartes  del Norte", "telefono": "", "correo": "",
    }, follow_redirects=True)

    html = respuesta.get_data(as_text=True)
    assert "Se registró el proveedor Autopartes del Norte." in html
    assert "800111222-3" in html


@pytest.mark.parametrize("datos, error", [
    ({"nit": "900.123.456", "nombre": "X"}, "Usa solo números"),
    ({"nit": "800111222", "nombre": ""}, "Escribe el nombre del proveedor."),
    ({"nit": "800111222", "nombre": "X", "correo": "sin-arroba"}, "Escribe un correo válido"),
    ({"nit": "900123456-7", "nombre": "X"}, "Este NIT ya es de Distribuidora Andina."),
])
def test_la_pantalla_valida_el_proveedor(client, base_compra, iniciar_sesion, datos, error):
    iniciar_sesion(base_compra["administrador"])

    respuesta = client.post("/compras/proveedores/nuevo", data=datos)

    assert error in respuesta.get_data(as_text=True)
    assert contar(Proveedor) == 1


def test_la_pantalla_edita_un_proveedor(client, base_compra, iniciar_sesion):
    iniciar_sesion(base_compra["administrador"])
    proveedor = base_compra["proveedor"]

    client.post(f"/compras/proveedores/{proveedor.id_proveedor}/editar", data={
        "nit": proveedor.nit, "nombre": "Distribuidora Andina SAS", "telefono": "", "correo": "",
    })

    assert db.session.get(Proveedor, proveedor.id_proveedor).nombre == "Distribuidora Andina SAS"


def test_editar_un_proveedor_que_no_existe_da_404(client, crear_cuenta, iniciar_sesion):
    iniciar_sesion(crear_cuenta("administrador"))
    assert client.get("/compras/proveedores/999/editar").status_code == 404


def datos_compra(base, lineas):
    datos = {"id_proveedor": str(base["proveedor"].id_proveedor)}
    for numero, (repuesto, cantidad, costo) in enumerate(lineas):
        datos[f"lineas-{numero}-id_repuesto"] = str(base[repuesto].id_repuesto)
        datos[f"lineas-{numero}-cantidad"] = cantidad
        datos[f"lineas-{numero}-costo_unitario"] = costo
    return datos


def test_la_pantalla_registra_la_compra_y_muestra_el_detalle(client, base_compra, iniciar_sesion):
    iniciar_sesion(base_compra["administrador"])

    respuesta = client.post("/compras/nueva", data=datos_compra(
        base_compra, [("filtro", "10", "12000"), ("pastillas", "1", "50000.50")],
    ), follow_redirects=True)

    html = respuesta.get_data(as_text=True)
    assert "Se registró la compra" in html
    assert "$170,000.50" in html
    assert "Distribuidora Andina" in html
    assert base_compra["filtro"].stock_actual == 12


def test_la_pantalla_pide_al_menos_un_repuesto_y_los_datos_de_cada_linea(client, base_compra, iniciar_sesion):
    iniciar_sesion(base_compra["administrador"])

    sin_lineas = client.post("/compras/nueva", data=datos_compra(base_compra, []))
    sin_costo = client.post("/compras/nueva", data=datos_compra(base_compra, [("filtro", "2", "")]))

    assert "Agrega al menos un repuesto a la compra." in sin_lineas.get_data(as_text=True)
    assert "Escribe el costo de cada repuesto." in sin_costo.get_data(as_text=True)
    assert contar(Compra) == 0


def test_la_lista_muestra_las_compras_y_el_formulario_elige_el_proveedor(client, base_compra, iniciar_sesion):
    services.registrar_compra(base_compra["proveedor"], base_compra["administrador"], [
        (base_compra["filtro"].id_repuesto, 3, Decimal("1000")),
    ])
    iniciar_sesion(base_compra["administrador"])
    id_proveedor = base_compra["proveedor"].id_proveedor

    lista = client.get("/compras/").get_data(as_text=True)
    formulario = client.get(f"/compras/nueva?proveedor={id_proveedor}").get_data(as_text=True)

    assert "Distribuidora Andina" in lista
    assert "$3,000.00" in lista
    assert f'<option selected value="{id_proveedor}">' in formulario


def test_sin_proveedores_el_formulario_avisa_que_hay_que_registrar_uno(client, crear_cuenta, iniciar_sesion):
    iniciar_sesion(crear_cuenta("administrador"))

    assert "Todavía no hay proveedores." in client.get("/compras/nueva").get_data(as_text=True)


def test_ver_una_compra_que_no_existe_da_404(client, crear_cuenta, iniciar_sesion):
    iniciar_sesion(crear_cuenta("administrador"))
    assert client.get("/compras/999").status_code == 404
