"""Pruebas del informe consolidado de sedes: conexión con la API de la otra sede,
traducción de sus datos al formato común, filtros, totales y la vista."""
import io
import json
from datetime import date, datetime
from decimal import Decimal
from urllib import error as url_error

import pytest

from app.cli import estados_venta
from app.consolidado import sedes, services
from app.extensions import db
from app.models import Cliente, Compra, EstadoVenta, Proveedor, Venta

# Respuestas como las de la API Django REST del grupo UD1 (sus serializers).
UD1 = {
    ("POST", "/auth/login/"): {"access": "jwt-de-prueba", "refresh": "x", "rol": "administrador"},
    ("GET", "/clientes/"): [
        {"id_cliente": 1, "nombres": "Valeria", "apellidos": "Pérez Gómez", "documento": "52123456"},
        {"id_cliente": 2, "nombres": "Tomás", "apellidos": "Ríos", "documento": None},
    ],
    ("GET", "/proveedores/"): [{"id_proveedor": 7, "nombre": "Compupartes Cali", "telefono": None, "contacto": None}],
    ("GET", "/ventas/"): [
        {"id_venta": 10, "id_cliente": 1, "fecha": "2026-10-20T15:30:00-05:00", "total": "238000.00", "estado": "activa"},
        {"id_venta": 11, "id_cliente": 2, "fecha": "2026-10-21T02:00:00Z", "total": "119000.00", "estado": "activa"},
        {"id_venta": 12, "id_cliente": 1, "fecha": "2026-10-22T09:00:00-05:00", "total": "50000.00", "estado": "anulada"},
        {"id_venta": 13, "id_cliente": 1, "fecha": "2026-11-02T09:00:00-05:00", "total": "70000.00", "estado": "activa"},
    ],
    ("GET", "/lotes/"): [
        {"id_lote": 3, "id_proveedor": 7, "id_pieza": 1, "cantidad": 4, "costo_unitario": "150000.00", "fecha_compra": "2026-10-05"},
        {"id_lote": 4, "id_proveedor": 7, "id_pieza": 2, "cantidad": 1, "costo_unitario": "10000.00", "fecha_compra": "2026-09-30"},
    ],
}
OCTUBRE = (date(2026, 10, 1), date(2026, 10, 31))


@pytest.fixture(autouse=True)
def sin_tokens_guardados():
    """Cada prueba empieza sin el token de UD1 guardado por otra."""
    sedes.olvidar_tokens()
    yield
    sedes.olvidar_tokens()


@pytest.fixture()
def otra_sede(app, monkeypatch):
    """Configura la otra sede como UD1 y responde con UD1 en lugar de hacer HTTP.
    Devuelve las peticiones que se hicieron."""
    app.config.update(
        SEDE_REMOTA_URL="http://ud1.local/api", SEDE_REMOTA_TIPO="ud1", SEDE_REMOTA_NOMBRE="Sede Cali",
        SEDE_REMOTA_USUARIO="admin", SEDE_REMOTA_CLAVE="clave",
    )
    peticiones = []

    def falso(metodo, ruta, cuerpo=None, token=None):
        peticiones.append((metodo, ruta, cuerpo, token))
        return UD1[(metodo, ruta)]

    monkeypatch.setattr(sedes, "_pedir", falso)
    return peticiones


@pytest.fixture()
def sede_local(app, crear_cuenta):
    """En RepuAuto: una venta completada, una cancelada y una compra en octubre."""
    estados_venta()
    administrador = crear_cuenta("administrador")
    vendedor = crear_cuenta("vendedor")
    estados = {e.nombre: e for e in db.session.scalars(db.select(EstadoVenta))}
    cliente = Cliente(cedula="1098000001", nombres="Carlos Andrés", apellidos="Rueda")
    db.session.add_all([
        Venta(cliente=cliente, vendedor=vendedor, estado=estados["Completada"], metodo_pago="Efectivo",
              total=Decimal("119000.00"), fecha=datetime(2026, 10, 30, 10, 15)),
        Venta(cliente=cliente, vendedor=vendedor, estado=estados["Cancelada"], metodo_pago="Efectivo",
              total=Decimal("999000.00"), fecha=datetime(2026, 10, 12, 10, 0)),
        Compra(proveedor=Proveedor(nit="900123456-7", nombre="Autopartes del Oriente"), usuario=administrador,
               total=Decimal("675000.00"), fecha=datetime(2026, 10, 4, 9, 30)),
    ])
    db.session.commit()
    return administrador


# ---------- Traducción de la API de UD1 ----------


def test_las_ventas_y_lotes_de_ud1_se_traducen_al_formato_comun(otra_sede):
    facturas = sedes.facturas_remotas(*OCTUBRE)

    assert facturas == [
        {
            "tipo": "venta", "numero": "V-000010", "fecha": "2026-10-20T15:30:00-05:00",
            "tercero": {"documento": "52123456", "nombre": "Valeria Pérez Gómez"},
            "subtotal": "200000.00", "iva": "38000.00", "total": "238000.00",
        },
        {
            "tipo": "venta", "numero": "V-000011", "fecha": "2026-10-20T21:00:00-05:00",
            "tercero": {"documento": "", "nombre": "Tomás Ríos"},
            "subtotal": "100000.00", "iva": "19000.00", "total": "119000.00",
        },
        {
            "tipo": "compra", "numero": "L-000003", "fecha": "2026-10-05T00:00:00-05:00",
            "tercero": {"documento": "", "nombre": "Compupartes Cali"},
            "subtotal": "504201.68", "iva": "95798.32", "total": "600000.00",
        },
    ]


def test_con_ud1_se_inicia_sesion_y_se_usa_su_token(otra_sede):
    sedes.facturas_remotas(*OCTUBRE)

    assert otra_sede[0] == ("POST", "/auth/login/", {"username": "admin", "password": "clave"}, None)
    assert all(token == "jwt-de-prueba" for _, _, _, token in otra_sede[1:])


def test_las_listas_paginadas_de_ud1_se_leen_completas(otra_sede, monkeypatch):
    paginas = {
        # Detrás de ngrok, Django puede armar el enlace con http y otro host: se usa solo la ruta.
        ("GET", "/ventas/"): {"results": [UD1[("GET", "/ventas/")][0]], "next": "http://otro-host/api/ventas/?page=2"},
        ("GET", "/ventas/?page=2"): {"results": [UD1[("GET", "/ventas/")][1]], "next": None},
    }
    monkeypatch.setattr(sedes, "_pedir", lambda metodo, ruta, cuerpo=None, token=None: paginas.get((metodo, ruta)) or UD1[(metodo, ruta)])

    numeros = [f["numero"] for f in sedes.facturas_remotas(*OCTUBRE) if f["tipo"] == "venta"]

    assert numeros == ["V-000010", "V-000011"]


def test_el_token_de_ud1_se_reutiliza_entre_consultas(otra_sede):
    sedes.facturas_remotas(*OCTUBRE)
    sedes.facturas_remotas(*OCTUBRE)

    assert [ruta for metodo, ruta, _, _ in otra_sede].count("/auth/login/") == 1


def test_el_token_guardado_vence(otra_sede, monkeypatch):
    sedes.facturas_remotas(*OCTUBRE)
    ahora = sedes.reloj.monotonic()
    monkeypatch.setattr(sedes.reloj, "monotonic", lambda: ahora + sedes.TOKEN_SEGUNDOS + 1)

    sedes.facturas_remotas(*OCTUBRE)

    assert [ruta for metodo, ruta, _, _ in otra_sede].count("/auth/login/") == 2


def test_una_sede_con_nuestro_formato_se_lee_directo(app, monkeypatch):
    app.config.update(SEDE_REMOTA_URL="http://otra.local/api", SEDE_REMOTA_TIPO="repuauto",
                      SEDE_REMOTA_USUARIO="admin@otra.com", SEDE_REMOTA_CLAVE="clave")
    factura = {"tipo": "venta", "numero": "V-000001", "fecha": "2026-10-01T10:00:00-05:00",
               "tercero": {"documento": "1", "nombre": "Ana"}, "subtotal": "1.00", "iva": "0.19", "total": "1.19"}
    respuestas = {"/login": {"token": "t"}, "/facturas?desde=2026-10-01&hasta=2026-10-31": {"facturas": [factura]}}
    monkeypatch.setattr(sedes, "_pedir", lambda metodo, ruta, cuerpo=None, token=None: respuestas[ruta])

    assert sedes.facturas_remotas(*OCTUBRE) == [factura]


# ---------- Errores de conexión ----------


def test_sin_configurar_la_otra_sede_no_esta_disponible(app):
    app.config["SEDE_REMOTA_URL"] = ""

    with pytest.raises(sedes.SedeNoDisponible, match="no está configurada"):
        sedes.facturas_remotas(*OCTUBRE)


def test_si_el_servidor_no_responde_se_avisa(otra_sede, monkeypatch):
    monkeypatch.undo()

    def sin_conexion(*args, **kwargs):
        raise url_error.URLError("Connection refused")

    monkeypatch.setattr(sedes.request, "urlopen", sin_conexion)

    with pytest.raises(sedes.SedeNoDisponible, match="¿Está encendido su servidor?"):
        sedes.facturas_remotas(*OCTUBRE)


def test_si_rechaza_el_usuario_se_avisa(otra_sede, monkeypatch):
    monkeypatch.undo()

    def rechazo(peticion, timeout):
        raise url_error.HTTPError(peticion.full_url, 401, "Unauthorized", {}, io.BytesIO(b"{}"))

    monkeypatch.setattr(sedes.request, "urlopen", rechazo)

    with pytest.raises(sedes.SedeNoDisponible, match="rechazó el usuario"):
        sedes.facturas_remotas(*OCTUBRE)


@pytest.mark.parametrize("codigo, encabezados, mensaje", [
    (400, {}, "DJANGO_ALLOWED_HOSTS"),
    (404, {"ngrok-error-code": "ERR_NGROK_3200"}, "ERR_NGROK_3200"),
    (404, {}, "todavía no tiene /auth/login/"),
    (429, {}, "Espera un minuto"),
])
def test_los_errores_tipicos_de_ngrok_y_django_se_explican(app, otra_sede, monkeypatch, codigo, encabezados, mensaje):
    monkeypatch.undo()
    app.config["SEDE_REMOTA_URL"] = "https://abcd-1234.ngrok-free.app/api"

    def falla(peticion, timeout):
        raise url_error.HTTPError(peticion.full_url, codigo, "error", encabezados, io.BytesIO(b""))

    monkeypatch.setattr(sedes.request, "urlopen", falla)

    with pytest.raises(sedes.SedeNoDisponible, match=mensaje):
        sedes.facturas_remotas(*OCTUBRE)


def test_la_peticion_http_lleva_el_json_y_el_token(app, monkeypatch):
    app.config["SEDE_REMOTA_URL"] = "http://ud1.local/api/"
    vistas = []

    class Respuesta(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def urlopen(peticion, timeout):
        vistas.append(peticion)
        return Respuesta(b'{"ok": true}')

    monkeypatch.setattr(sedes.request, "urlopen", urlopen)

    assert sedes._pedir("POST", "/auth/login/", {"username": "a"}, token="t") == {"ok": True}
    assert vistas[0].full_url == "http://ud1.local/api/auth/login/"
    assert json.loads(vistas[0].data) == {"username": "a"}
    assert vistas[0].get_header("Authorization") == "Bearer t"
    assert vistas[0].get_header("Ngrok-skip-browser-warning") == "true"


def test_datos_que_no_se_entienden_se_avisan(otra_sede, monkeypatch):
    monkeypatch.setattr(sedes, "_pedir", lambda metodo, ruta, cuerpo=None, token=None: {"sin": "access"})

    with pytest.raises(sedes.SedeNoDisponible, match="no se entienden"):
        sedes.facturas_remotas(*OCTUBRE)


# ---------- Informe consolidado ----------


def test_el_informe_junta_las_dos_sedes_y_suma_por_sede(sede_local, otra_sede):
    datos = services.informe(*OCTUBRE)

    assert datos["aviso"] is None
    assert datos["sucursales"] == ["Bucaramanga", "Sede Cali"]
    # De la más reciente a la más antigua: la venta del 30 de octubre aquí y la del 20 en Cali.
    assert [(f["sucursal"], f["tipo"]) for f in datos["facturas"]][:2] == [("Bucaramanga", "venta"), ("Sede Cali", "venta")]
    assert datos["facturas"][1]["numero"] == "V-000011"
    bucaramanga, cali = datos["por_sucursal"]
    assert (bucaramanga["venta"]["total"], bucaramanga["compra"]["total"]) == (Decimal("119000.00"), Decimal("675000.00"))
    assert (cali["venta"]["cantidad"], cali["venta"]["total"]) == (2, Decimal("357000.00"))
    assert datos["totales"]["venta"]["total"] == Decimal("476000.00")
    assert datos["totales"]["compra"]["total"] == Decimal("1275000.00")
    assert datos["totales"]["diferencia"] == Decimal("-799000.00")


@pytest.mark.parametrize("filtros, numeros", [
    ({"tipo": "compra"}, {"C-", "L-"}),
    ({"sucursal": "Sede Cali", "tipo": "venta"}, {"V-"}),
    ({"tercero": "perez"}, {"V-"}),
    ({"tercero": "900123456"}, {"C-"}),
])
def test_el_informe_filtra_por_tipo_sede_y_tercero(sede_local, otra_sede, filtros, numeros):
    datos = services.informe(*OCTUBRE, **filtros)

    assert {f["numero"][:2] for f in datos["facturas"]} == numeros


def test_el_filtro_por_tercero_ignora_tildes_y_mayusculas(sede_local, otra_sede):
    datos = services.informe(*OCTUBRE, tercero="TOMAS rios")

    assert [f["tercero"]["nombre"] for f in datos["facturas"]] == ["Tomás Ríos"]


def test_si_la_otra_sede_falla_el_informe_trae_solo_esta_sede(app, sede_local):
    app.config["SEDE_REMOTA_URL"] = ""

    datos = services.informe(*OCTUBRE)

    assert "no está configurada" in datos["aviso"]
    assert {f["sucursal"] for f in datos["facturas"]} == {"Bucaramanga"}


# ---------- Vista ----------


@pytest.mark.parametrize("rol", ["cliente", "vendedor"])
def test_solo_el_administrador_ve_el_consolidado(client, crear_cuenta, iniciar_sesion, rol):
    iniciar_sesion(crear_cuenta(rol))

    assert client.get("/consolidado/").status_code == 403


def test_la_vista_muestra_las_dos_sedes(client, iniciar_sesion, sede_local, otra_sede):
    iniciar_sesion(sede_local)

    html = client.get("/consolidado/?desde=2026-10-01&hasta=2026-10-31").get_data(as_text=True)

    assert "Sede Cali" in html and "Bucaramanga" in html
    assert "Valeria Pérez Gómez" in html
    assert "L-000003" in html
    assert "$476,000.00" in html
    assert "Consolidado de sedes" in html


def test_la_vista_avisa_si_la_otra_sede_no_responde(app, client, iniciar_sesion, sede_local):
    app.config["SEDE_REMOTA_URL"] = ""
    iniciar_sesion(sede_local)

    html = client.get("/consolidado/?desde=2026-10-01&hasta=2026-10-31").get_data(as_text=True)

    assert "Sin datos de Sede UD1." in html
    assert "$119,000.00" in html


# ---------- Inventario de las dos sedes ----------

INVENTARIO_UD1 = {
    "sucursal": "Cali", "fecha": "2026-11-10T10:00:00-05:00", "moneda": "COP",
    "resumen": {"productos": 2, "unidades": 7, "valor": "9100000.00", "en_stock": 1, "stock_bajo": 0, "agotado": 1},
    "productos": [
        {"codigo": "GPU-1", "nombre": "Tarjeta de video", "categoria": "Gráficas", "marca": "Nvidia", "stock": 7,
         "stock_minimo": 2, "precio_venta": "1300000.00", "valor": "9100000.00", "estado": "en_stock"},
        {"codigo": "RAM-1", "nombre": "Memoria RAM", "categoria": "Memorias", "marca": "Kingston", "stock": 0,
         "stock_minimo": 3, "precio_venta": "180000.00", "valor": "0.00", "estado": "agotado"},
    ],
}


@pytest.fixture()
def otra_sede_inventario(app, monkeypatch):
    app.config.update(
        SEDE_REMOTA_URL="https://ud1.ngrok-free.dev/api", SEDE_REMOTA_TIPO="repuauto", SEDE_REMOTA_NOMBRE="Sede Cali",
        SEDE_REMOTA_USUARIO="repuauto@pcstock.com", SEDE_REMOTA_CLAVE="clave",
    )
    respuestas = {("POST", "/login"): {"token": "t"}, ("GET", "/inventario"): INVENTARIO_UD1}
    monkeypatch.setattr(sedes, "_pedir", lambda metodo, ruta, cuerpo=None, token=None: respuestas[(metodo, ruta)])


@pytest.fixture()
def inventario_local(app):
    from app.models import Categoria, MarcaRepuesto, Repuesto

    db.session.add(Repuesto(
        codigo="FRE-1", nombre="Pastillas de freno", categoria=Categoria(nombre="Frenos"),
        marca=MarcaRepuesto(nombre="Bosch"), stock_actual=2, stock_minimo=4, precio_venta=Decimal("100000.00"),
    ))
    db.session.commit()


def test_el_inventario_remoto_se_lee_con_nuestro_formato(otra_sede_inventario):
    remoto = sedes.inventario_remoto()

    assert remoto["resumen"]["productos"] == 2
    assert [p["codigo"] for p in remoto["productos"]] == ["GPU-1", "RAM-1"]


def test_con_la_api_anterior_de_ud1_no_hay_inventario(app):
    app.config.update(SEDE_REMOTA_URL="http://ud1.local/api", SEDE_REMOTA_TIPO="ud1")

    with pytest.raises(sedes.SedeNoDisponible, match="SEDE_REMOTA_TIPO=repuauto"):
        sedes.inventario_remoto()


def test_si_la_otra_sede_no_publica_inventario_se_dice_claramente(app, monkeypatch):
    app.config.update(SEDE_REMOTA_URL="https://ud1.ngrok-free.dev/api", SEDE_REMOTA_TIPO="repuauto",
                      SEDE_REMOTA_USUARIO="u", SEDE_REMOTA_CLAVE="c")
    monkeypatch.setattr(sedes, "_token_repuauto", lambda: "t")

    def no_existe(peticion, timeout):
        # Así responde el Django de UD1 en modo de depuración: una página HTML, sin encabezado de ngrok.
        raise url_error.HTTPError(peticion.full_url, 404, "Not Found", {}, io.BytesIO(b"<html>Page not found</html>"))

    monkeypatch.setattr(sedes.request, "urlopen", no_existe)

    with pytest.raises(sedes.SedeNoDisponible, match="todavía no tiene /inventario"):
        sedes.inventario_remoto()


def test_el_inventario_consolidado_suma_las_dos_sedes(inventario_local, otra_sede_inventario):
    datos = services.inventario()

    assert datos["aviso"] is None
    assert [(f["sucursal"], f["productos"], f["valor"]) for f in datos["por_sucursal"]] == [
        ("Bucaramanga", 1, Decimal("200000.00")), ("Sede Cali", 2, Decimal("9100000.00")),
    ]
    assert datos["totales"]["productos"] == 3
    assert datos["totales"]["valor"] == Decimal("9300000.00")
    assert (datos["totales"]["stock_bajo"], datos["totales"]["agotado"]) == (1, 1)
    assert {p["sucursal"] for p in datos["productos"]} == {"Bucaramanga", "Sede Cali"}


@pytest.mark.parametrize("filtros, codigos", [
    ({"estado": "agotado"}, ["RAM-1"]),
    ({"sucursal": "Bucaramanga"}, ["FRE-1"]),
    ({"buscar": "graficas"}, ["GPU-1"]),
    ({"buscar": "bosch"}, ["FRE-1"]),
])
def test_el_inventario_consolidado_se_filtra(inventario_local, otra_sede_inventario, filtros, codigos):
    assert [p["codigo"] for p in services.inventario(**filtros)["productos"]] == codigos


def test_la_pestana_inventario_muestra_las_dos_sedes(client, crear_cuenta, iniciar_sesion, inventario_local, otra_sede_inventario):
    iniciar_sesion(crear_cuenta("administrador"))

    html = client.get("/consolidado/inventario").get_data(as_text=True)

    assert "Tarjeta de video" in html and "Pastillas de freno" in html
    assert "$9,300,000.00" in html
    assert 'href="/consolidado/inventario"' in html and 'href="/consolidado/"' in html


def test_la_pestana_inventario_avisa_si_la_otra_sede_no_responde(client, crear_cuenta, iniciar_sesion, inventario_local):
    iniciar_sesion(crear_cuenta("administrador"))

    html = client.get("/consolidado/inventario").get_data(as_text=True)

    assert "Sin inventario de Sede UD1." in html
    assert "Pastillas de freno" in html


@pytest.mark.parametrize("rol", ["cliente", "vendedor"])
def test_solo_el_administrador_ve_el_inventario_consolidado(client, crear_cuenta, iniciar_sesion, rol):
    iniciar_sesion(crear_cuenta(rol))

    assert client.get("/consolidado/inventario").status_code == 403
