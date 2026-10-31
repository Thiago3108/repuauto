"""Pruebas de US-05: consultar catálogo de repuestos con filtro en cascada por vehículo."""
from decimal import Decimal

import pytest

from app.catalogo import services
from app.extensions import db
from app.models import Categoria, MarcaRepuesto, Repuesto
from app.vehiculos import services as vehiculos_services


def crear_repuesto(
    codigo="FRE-001",
    nombre="Pastillas de freno",
    categoria="Frenos",
    marca="Bosch",
    precio="85000.00",
    stock=5,
    activo=True,
):
    cat = db.session.scalar(db.select(Categoria).filter_by(nombre=categoria))
    if cat is None:
        cat = Categoria(nombre=categoria)
        db.session.add(cat)

    marca_obj = db.session.scalar(db.select(MarcaRepuesto).filter_by(nombre=marca))
    if marca_obj is None:
        marca_obj = MarcaRepuesto(nombre=marca)
        db.session.add(marca_obj)

    db.session.flush()
    repuesto = Repuesto(
        codigo=codigo,
        nombre=nombre,
        precio_venta=Decimal(precio),
        stock_actual=stock,
        stock_minimo=2,
        id_categoria=cat.id_categoria,
        id_marca_repuesto=marca_obj.id_marca_repuesto,
        activo=activo,
    )
    db.session.add(repuesto)
    db.session.commit()
    return repuesto


# ---------- Listar y filtrar repuestos (T1) ----------


def test_el_catalogo_solo_muestra_repuestos_activos(app):
    activo = crear_repuesto(codigo="FRE-001", nombre="Pastillas activas", activo=True)
    crear_repuesto(codigo="FRE-002", nombre="Pastillas inactivas", activo=False)

    assert services.consultar_catalogo() == [activo]


def test_busqueda_por_nombre_o_codigo_y_filtro_por_categoria(app):
    pastillas = crear_repuesto(codigo="FRE-001", nombre="Pastillas cerámicas", categoria="Frenos")
    filtro = crear_repuesto(codigo="FIL-010", nombre="Filtro de aire", categoria="Filtros")

    assert services.consultar_catalogo(busqueda="FRE-001") == [pastillas]
    assert services.consultar_catalogo(busqueda="aire") == [filtro]
    assert services.consultar_catalogo(id_categoria=pastillas.id_categoria) == [pastillas]


# ---------- Filtro en cascada por vehículo: Marca -> Línea -> Año (T2) ----------


def test_cascada_de_vehiculos_marca_linea_y_anio(app):
    corolla_2018 = vehiculos_services.crear_vehiculo("Toyota", "Corolla", 2018, "XEi")
    vehiculos_services.crear_vehiculo("Toyota", "Corolla", 2020, "SEG")
    vehiculos_services.crear_vehiculo("Toyota", "Hilux", 2019)
    vehiculos_services.crear_vehiculo("Renault", "Logan", 2015)

    id_toyota = corolla_2018.id_marca_vehiculo

    assert services.listar_lineas_por_marca(id_toyota) == ["Corolla", "Hilux"]
    assert services.listar_anios_por_marca_y_linea(id_toyota, "Corolla") == [2020, 2018]
    assert services.listar_anios_por_marca_y_linea(id_toyota, "Logan") == []

    # Si la línea no pertenece a la marca, la cascada reinicia línea y año.
    cascada_invalida = services.normalizar_filtro_vehiculo(id_toyota, "Logan", 2015)
    assert cascada_invalida["id_marca"] == id_toyota
    assert cascada_invalida["linea"] is None
    assert cascada_invalida["anio"] is None

    # Si el año no pertenece a la línea, la cascada conserva marca y línea y reinicia año.
    cascada_anio_invalido = services.normalizar_filtro_vehiculo(id_toyota, "corolla", 1999)
    assert cascada_anio_invalido["id_marca"] == id_toyota
    assert cascada_anio_invalido["linea"] == "Corolla"
    assert cascada_anio_invalido["anio"] is None


def test_filtrar_catalogo_por_marca_linea_y_anio_en_cascada(app):
    corolla_18 = vehiculos_services.crear_vehiculo("Toyota", "Corolla", 2018, "XEi")
    corolla_18_seg = vehiculos_services.crear_vehiculo("Toyota", "Corolla", 2018, "SEG")
    corolla_20 = vehiculos_services.crear_vehiculo("Toyota", "Corolla", 2020)
    hilux_19 = vehiculos_services.crear_vehiculo("Toyota", "Hilux", 2019)
    logan_16 = vehiculos_services.crear_vehiculo("Renault", "Logan", 2016)

    rep_corolla_18 = crear_repuesto(codigo="TOY-18", nombre="Pastilla Corolla 2018")
    rep_corolla_20 = crear_repuesto(codigo="TOY-20", nombre="Pastilla Corolla 2020")
    rep_hilux = crear_repuesto(codigo="TOY-HI", nombre="Amortiguador Hilux")
    rep_logan = crear_repuesto(codigo="REN-LO", nombre="Filtro Logan")

    # El mismo repuesto sirve a dos referencias del Corolla 2018: no debe salir duplicado.
    vehiculos_services.asociar_repuesto(corolla_18, rep_corolla_18)
    vehiculos_services.asociar_repuesto(corolla_18_seg, rep_corolla_18)
    vehiculos_services.asociar_repuesto(corolla_20, rep_corolla_20)
    vehiculos_services.asociar_repuesto(hilux_19, rep_hilux)
    vehiculos_services.asociar_repuesto(logan_16, rep_logan)

    id_toyota = corolla_18.id_marca_vehiculo

    # 1. Solo marca Toyota -> los 3 repuestos de Toyota
    por_marca = services.consultar_catalogo(id_marca_vehiculo=id_toyota)
    assert [r.codigo for r in por_marca] == ["TOY-HI", "TOY-18", "TOY-20"]

    # 2. Marca Toyota + Línea Corolla -> los 2 de Corolla
    por_linea = services.consultar_catalogo(id_marca_vehiculo=id_toyota, linea="Corolla")
    assert [r.codigo for r in por_linea] == ["TOY-18", "TOY-20"]

    # 3. Marca Toyota + Línea Corolla + Año 2018 -> solo el de 2018, sin duplicados
    por_anio = services.consultar_catalogo(id_marca_vehiculo=id_toyota, linea="Corolla", anio=2018)
    assert [r.codigo for r in por_anio] == ["TOY-18"]


# ---------- Vista UI-04 y acceso para los tres roles (T3 y T4) ----------


@pytest.mark.parametrize("rol", ["cliente", "vendedor", "administrador"])
def test_los_tres_roles_pueden_consultar_el_catalogo(client, crear_cuenta, iniciar_sesion, rol):
    iniciar_sesion(crear_cuenta(rol))

    assert client.get("/catalogo/").status_code == 200


def test_la_vista_muestra_disponibilidad_y_filtra_por_vehiculo(client, crear_cuenta, iniciar_sesion):
    iniciar_sesion(crear_cuenta("cliente"))
    corolla = vehiculos_services.crear_vehiculo("Toyota", "Corolla", 2018)
    logan = vehiculos_services.crear_vehiculo("Renault", "Logan", 2015)

    en_stock = crear_repuesto(codigo="FRE-001", nombre="Pastillas Corolla", stock=8)
    agotado = crear_repuesto(codigo="FIL-002", nombre="Filtro Logan", stock=0)
    vehiculos_services.asociar_repuesto(corolla, en_stock)
    vehiculos_services.asociar_repuesto(logan, agotado)

    html_todo = client.get("/catalogo/").get_data(as_text=True)
    assert "En stock (8)" in html_todo
    assert "Agotado" in html_todo

    html_filtrado = client.get(
        f"/catalogo/?id_marca={corolla.id_marca_vehiculo}&linea=Corolla&anio=2018"
    ).get_data(as_text=True)
    assert "Pastillas Corolla" in html_filtrado
    assert "Filtro Logan" not in html_filtrado


def test_endpoint_json_de_cascada_y_mensaje_sin_resultados(client, crear_cuenta, iniciar_sesion):
    iniciar_sesion(crear_cuenta("cliente"))
    corolla = vehiculos_services.crear_vehiculo("Toyota", "Corolla", 2018)

    datos = client.get(
        f"/catalogo/vehiculos-cascada?id_marca={corolla.id_marca_vehiculo}&linea=Corolla"
    ).get_json()
    assert datos == {"lineas": ["Corolla"], "anios": [2018]}

    html_vacio = client.get("/catalogo/?q=inexistente").get_data(as_text=True)
    assert "No se encontraron repuestos" in html_vacio
