"""Pruebas de US-03: gestionar vehículos y repuestos compatibles (T1, T2, T3 y T4)."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.cli import MARCAS_VEHICULO, marcas_vehiculo
from app.extensions import db
from app.models import Categoria, MarcaRepuesto, MarcaVehiculo, Repuesto, RepuestoVehiculo, Vehiculo
from app.vehiculos import services
from app.vehiculos.services import VehiculoRechazado


def nuevo(marca="Toyota", linea="Corolla", anio=2018, referencia="XEi 1.8"):
    return services.crear_vehiculo(marca=marca, linea=linea, anio=anio, referencia=referencia)


def crear_repuesto(codigo="FRE-001", nombre="Pastillas de freno", activo=True):
    categoria = db.session.scalar(db.select(Categoria).filter_by(nombre="Frenos"))
    if categoria is None:
        categoria = Categoria(nombre="Frenos")
        db.session.add(categoria)

    marca = db.session.scalar(db.select(MarcaRepuesto).filter_by(nombre="Bosch"))
    if marca is None:
        marca = MarcaRepuesto(nombre="Bosch")
        db.session.add(marca)

    db.session.flush()
    repuesto = Repuesto(
        codigo=codigo,
        nombre=nombre,
        precio_venta=Decimal("85000.00"),
        stock_actual=10,
        stock_minimo=2,
        id_categoria=categoria.id_categoria,
        id_marca_repuesto=marca.id_marca_repuesto,
        activo=activo,
    )
    db.session.add(repuesto)
    db.session.commit()
    return repuesto


def contar(modelo):
    return db.session.scalar(db.select(db.func.count()).select_from(modelo))


@pytest.fixture()
def admin(client, crear_cuenta, iniciar_sesion):
    iniciar_sesion(crear_cuenta("administrador"))
    return client


# ---------- Tablas (T1) ----------

def test_un_vehiculo_tiene_marca_linea_y_anio_y_la_referencia_es_opcional(app):
    marca = MarcaVehiculo(nombre="Mazda")
    vehiculo = Vehiculo(marca=marca, linea="3", anio=2015)
    db.session.add(vehiculo)
    db.session.commit()

    assert vehiculo.referencia is None
    assert vehiculo.descripcion == "Mazda 3 2015"
    assert marca.vehiculos == [vehiculo]


def test_el_nombre_de_la_marca_no_se_repite(app):
    db.session.add(MarcaVehiculo(nombre="Kia"))
    db.session.commit()

    with pytest.raises(IntegrityError):
        db.session.add(MarcaVehiculo(nombre="Kia"))
        db.session.commit()


def test_flask_seed_carga_las_marcas_sin_duplicarlas(app):
    marcas_vehiculo()
    marcas_vehiculo()
    db.session.commit()

    assert contar(MarcaVehiculo) == len(MARCAS_VEHICULO)


# ---------- Reglas de negocio (T2) ----------

def test_crear_vehiculo_limpia_los_espacios_y_crea_la_marca(app):
    vehiculo = nuevo(marca="  Toyota ", linea=" Corolla  Cross ", referencia="  ")

    assert vehiculo.id_vehiculo is not None
    assert vehiculo.marca.nombre == "Toyota"
    assert vehiculo.linea == "Corolla Cross"
    assert vehiculo.referencia is None


def test_la_marca_se_reutiliza_sin_importar_mayusculas(app):
    nuevo(marca="Chevrolet", linea="Spark")
    nuevo(marca="CHEVROLET", linea="Onix")

    assert contar(MarcaVehiculo) == 1
    assert {v.marca.nombre for v in services.listar_vehiculos()} == {"Chevrolet"}


def test_no_se_repite_un_vehiculo_con_los_mismos_datos(app):
    nuevo(marca="Toyota", linea="Corolla", referencia="XEi 1.8", anio=2018)

    with pytest.raises(VehiculoRechazado) as error:
        nuevo(marca="toyota", linea="corolla", referencia="xei 1.8", anio=2018)

    assert error.value.campo == "linea"
    assert contar(Vehiculo) == 1


def test_misma_linea_con_otro_anio_u_otra_referencia_si_se_permite(app):
    nuevo(anio=2018, referencia="XEi 1.8")
    nuevo(anio=2019, referencia="XEi 1.8")
    nuevo(anio=2018, referencia=None)

    assert contar(Vehiculo) == 3


@pytest.mark.parametrize("anio", ["18", "abcd", 1899, date.today().year + 2, None])
def test_el_anio_debe_ser_valido(app, anio):
    with pytest.raises(VehiculoRechazado) as error:
        nuevo(anio=anio)

    assert error.value.campo == "anio"
    assert contar(Vehiculo) == 0
    assert contar(MarcaVehiculo) == 0  # Si se rechaza, tampoco queda la marca nueva.


def test_se_aceptan_los_modelos_del_anio_siguiente(app):
    assert nuevo(anio=date.today().year + 1).anio == date.today().year + 1


@pytest.mark.parametrize("campo, datos", [
    ("marca", {"marca": "  "}),
    ("linea", {"linea": ""}),
    ("linea", {"linea": "x" * 61}),
    ("referencia", {"referencia": "x" * 61}),
])
def test_los_datos_obligatorios_y_las_longitudes_se_validan(app, campo, datos):
    with pytest.raises(VehiculoRechazado) as error:
        nuevo(**datos)

    assert error.value.campo == campo


def test_actualizar_vehiculo(app):
    vehiculo = nuevo()

    services.actualizar_vehiculo(vehiculo, marca="Mazda", linea="CX-5", anio=2020, referencia="Touring")

    db.session.expire_all()
    guardado = services.obtener_vehiculo(vehiculo.id_vehiculo)
    assert guardado.descripcion == "Mazda CX-5 Touring 2020"


def test_actualizar_sin_cambios_no_choca_consigo_mismo(app):
    vehiculo = nuevo()

    services.actualizar_vehiculo(vehiculo, marca="Toyota", linea="Corolla", anio=2018, referencia="XEi 1.8")

    assert contar(Vehiculo) == 1


def test_actualizar_no_puede_dejarlo_igual_a_otro(app):
    nuevo(linea="Corolla")
    otro = nuevo(linea="Yaris")

    with pytest.raises(VehiculoRechazado):
        services.actualizar_vehiculo(otro, marca="Toyota", linea="Corolla", anio=2018, referencia="XEi 1.8")

    db.session.expire_all()
    assert services.obtener_vehiculo(otro.id_vehiculo).linea == "Yaris"


def test_eliminar_vehiculo_no_borra_la_marca(app):
    vehiculo = nuevo()

    services.eliminar_vehiculo(vehiculo)

    assert contar(Vehiculo) == 0
    assert services.buscar_marca("Toyota") is not None


def test_la_busqueda_acepta_coincidencias_parciales(app):
    nuevo(marca="Toyota", linea="Corolla", anio=2018)
    nuevo(marca="Renault", linea="Logan", referencia="Expression", anio=2012)
    nuevo(marca="Chevrolet", linea="Spark", referencia="GT", anio=2016)

    assert [v.linea for v in services.listar_vehiculos("coro")] == ["Corolla"]
    assert [v.linea for v in services.listar_vehiculos("RENA")] == ["Logan"]
    assert [v.linea for v in services.listar_vehiculos("press")] == ["Logan"]
    assert [v.linea for v in services.listar_vehiculos("2016")] == ["Spark"]
    assert services.listar_vehiculos("Ferrari") == []
    assert len(services.listar_vehiculos("")) == 3


def test_la_lista_sale_ordenada_por_marca_linea_y_anio(app):
    nuevo(marca="Toyota", linea="Corolla", anio=2015)
    nuevo(marca="Chevrolet", linea="Spark", anio=2016)
    nuevo(marca="Toyota", linea="Corolla", anio=2020)

    assert [v.descripcion for v in services.listar_vehiculos()] == [
        "Chevrolet Spark XEi 1.8 2016",
        "Toyota Corolla XEi 1.8 2020",
        "Toyota Corolla XEi 1.8 2015",
    ]


# ---------- Repuestos compatibles (T3) ----------

def test_asociar_y_listar_repuestos_compatibles(app):
    vehiculo = nuevo()
    pastillas = crear_repuesto(codigo="FRE-001", nombre="Pastillas de freno")
    disco = crear_repuesto(codigo="FRE-002", nombre="Disco de freno")

    services.asociar_repuesto(vehiculo, pastillas.id_repuesto)

    assert services.listar_repuestos_compatibles(vehiculo) == [pastillas]
    assert services.listar_repuestos_disponibles(vehiculo) == [disco]
    assert vehiculo.repuestos == [pastillas]


def test_las_compatibilidades_no_se_duplican(app):
    vehiculo = nuevo()
    repuesto = crear_repuesto()
    services.asociar_repuesto(vehiculo, repuesto.id_repuesto)

    with pytest.raises(VehiculoRechazado) as error:
        services.asociar_repuesto(vehiculo, repuesto.id_repuesto)

    assert error.value.campo == "id_repuesto"
    assert contar(RepuestoVehiculo) == 1


def test_no_se_puede_asociar_un_repuesto_inexistente_o_inactivo(app):
    vehiculo = nuevo()
    inactivo = crear_repuesto(codigo="INA-001", activo=False)

    with pytest.raises(VehiculoRechazado):
        services.asociar_repuesto(vehiculo, 999)

    with pytest.raises(VehiculoRechazado):
        services.asociar_repuesto(vehiculo, inactivo.id_repuesto)

    assert contar(RepuestoVehiculo) == 0


def test_desasociar_repuesto_quita_el_enlace_pero_no_borra_el_repuesto(app):
    vehiculo = nuevo()
    repuesto = crear_repuesto()
    services.asociar_repuesto(vehiculo, repuesto.id_repuesto)

    assert services.desasociar_repuesto(vehiculo, repuesto.id_repuesto) is True
    assert services.desasociar_repuesto(vehiculo, repuesto.id_repuesto) is False
    assert contar(RepuestoVehiculo) == 0
    assert contar(Repuesto) == 1


def test_al_eliminar_un_vehiculo_se_eliminan_sus_compatibilidades_pero_no_los_repuestos(app):
    vehiculo = nuevo()
    otro = nuevo(linea="Yaris")
    repuesto = crear_repuesto()
    services.asociar_repuesto(vehiculo, repuesto.id_repuesto)
    services.asociar_repuesto(otro, repuesto.id_repuesto)

    services.eliminar_vehiculo(vehiculo)

    assert contar(Vehiculo) == 1
    assert contar(RepuestoVehiculo) == 1
    assert contar(Repuesto) == 1
    assert services.listar_repuestos_compatibles(otro) == [repuesto]


def test_filtrar_repuestos_disponibles_por_busqueda(app):
    vehiculo = nuevo()
    crear_repuesto(codigo="FRE-001", nombre="Pastillas delanteras")
    crear_repuesto(codigo="FIL-010", nombre="Filtro de aceite")

    assert [r.codigo for r in services.listar_repuestos_disponibles(vehiculo, "FIL")] == ["FIL-010"]
    assert [r.codigo for r in services.listar_repuestos_disponibles(vehiculo, "pastillas")] == ["FRE-001"]


# ---------- Vista UI-11 y acceso por rol (T4) ----------

@pytest.mark.parametrize("rol", ["cliente", "vendedor"])
def test_solo_el_administrador_entra(client, crear_cuenta, iniciar_sesion, rol):
    vehiculo = nuevo()
    iniciar_sesion(crear_cuenta(rol))

    assert client.get("/vehiculos/").status_code == 403
    assert client.post("/vehiculos/", data={"marca": "Kia", "linea": "Rio", "anio": "2019"}).status_code == 403
    assert client.get(f"/vehiculos/{vehiculo.id_vehiculo}/compatibles").status_code == 403
    assert client.post(
        f"/vehiculos/{vehiculo.id_vehiculo}/compatibles", data={"id_repuesto": "1"}
    ).status_code == 403


def test_sin_sesion_va_al_login(client):
    respuesta = client.get("/vehiculos/")

    assert respuesta.status_code == 302
    assert "/auth/login" in respuesta.headers["Location"]


def test_el_menu_del_administrador_muestra_vehiculos(admin):
    assert "Vehículos" in admin.get("/").get_data(as_text=True)


def test_la_vista_lista_los_vehiculos(admin):
    nuevo(marca="Renault", linea="Logan", anio=2012)

    html = admin.get("/vehiculos/").get_data(as_text=True)

    assert "Gestión de vehículos" in html
    assert "Logan" in html and "2012" in html


def test_la_vista_avisa_cuando_no_hay_resultados(admin):
    html = admin.get("/vehiculos/?q=Ferrari").get_data(as_text=True)

    assert "No hay vehículos que coincidan" in html


def test_registrar_vehiculo_desde_la_vista(admin):
    respuesta = admin.post(
        "/vehiculos/",
        data={"marca": "Kia", "linea": "Picanto", "referencia": "", "anio": "2021"},
        follow_redirects=True,
    )

    html = respuesta.get_data(as_text=True)
    assert "Vehículo registrado: Kia Picanto 2021." in html
    assert contar(Vehiculo) == 1


def test_un_anio_de_menos_de_4_digitos_muestra_el_error(admin):
    html = admin.post("/vehiculos/", data={"marca": "Kia", "linea": "Rio", "anio": "21"}).get_data(as_text=True)

    assert "El año debe tener 4 dígitos" in html
    assert contar(Vehiculo) == 0


def test_un_vehiculo_repetido_muestra_el_error(admin):
    nuevo(marca="Kia", linea="Rio", anio=2019, referencia=None)

    html = admin.post("/vehiculos/", data={"marca": "kia", "linea": "rio", "anio": "2019"}).get_data(as_text=True)

    assert "Ese vehículo ya está registrado." in html
    assert contar(Vehiculo) == 1


def test_editar_vehiculo_desde_la_vista(admin):
    vehiculo = nuevo()
    url = f"/vehiculos/{vehiculo.id_vehiculo}/editar"

    formulario = admin.get(url).get_data(as_text=True)
    assert 'value="Corolla"' in formulario

    respuesta = admin.post(
        url, data={"marca": "Toyota", "linea": "Corolla", "referencia": "SEG", "anio": "2019"},
        follow_redirects=True,
    )

    assert "Vehículo actualizado: Toyota Corolla SEG 2019." in respuesta.get_data(as_text=True)


def test_eliminar_vehiculo_desde_la_vista(admin):
    vehiculo = nuevo()

    respuesta = admin.post(f"/vehiculos/{vehiculo.id_vehiculo}/eliminar", follow_redirects=True)

    assert "Vehículo eliminado" in respuesta.get_data(as_text=True)
    assert contar(Vehiculo) == 0


def test_eliminar_solo_acepta_post(admin):
    vehiculo = nuevo()

    assert admin.get(f"/vehiculos/{vehiculo.id_vehiculo}/eliminar").status_code == 405
    assert contar(Vehiculo) == 1


def test_asociar_y_quitar_repuesto_compatible_desde_la_vista(admin):
    vehiculo = nuevo()
    repuesto = crear_repuesto(codigo="FRE-001", nombre="Pastillas de freno")
    url = f"/vehiculos/{vehiculo.id_vehiculo}/compatibles"

    respuesta = admin.post(url, data={"id_repuesto": str(repuesto.id_repuesto)}, follow_redirects=True)
    html = respuesta.get_data(as_text=True)
    assert "Se asoció el repuesto Pastillas de freno (FRE-001)" in html
    assert contar(RepuestoVehiculo) == 1

    respuesta = admin.post(f"{url}/{repuesto.id_repuesto}/quitar", follow_redirects=True)
    assert "Se quitó la compatibilidad del repuesto." in respuesta.get_data(as_text=True)
    assert contar(RepuestoVehiculo) == 0
    assert contar(Repuesto) == 1


def test_asociar_un_repuesto_repetido_desde_la_vista_muestra_el_error(admin):
    vehiculo = nuevo()
    repuesto = crear_repuesto()
    services.asociar_repuesto(vehiculo, repuesto.id_repuesto)

    respuesta = admin.post(
        f"/vehiculos/{vehiculo.id_vehiculo}/compatibles",
        data={"id_repuesto": str(repuesto.id_repuesto)},
    )

    assert "Ese repuesto ya está asociado con este vehículo." in respuesta.get_data(as_text=True)
    assert contar(RepuestoVehiculo) == 1


@pytest.mark.parametrize("metodo, ruta", [
    ("get", "/vehiculos/999/editar"),
    ("post", "/vehiculos/999/eliminar"),
    ("get", "/vehiculos/999/compatibles"),
    ("post", "/vehiculos/999/compatibles"),
    ("post", "/vehiculos/999/compatibles/1/quitar"),
])
def test_un_vehiculo_que_no_existe_da_404(admin, metodo, ruta):
    assert getattr(admin, metodo)(ruta).status_code == 404
