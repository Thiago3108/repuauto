"""Pruebas de la API REST para la integración entre sedes: login con token y facturas."""
from datetime import datetime
from decimal import Decimal

import pytest
from itsdangerous import URLSafeTimedSerializer

from app.api import services
from app.cli import estados_venta
from app.extensions import db
from app.models import Categoria, Cliente, Compra, EstadoVenta, MarcaRepuesto, Proveedor, Repuesto, Venta
from tests.conftest import CLAVE


@pytest.fixture()
def administrador(crear_cuenta):
    return crear_cuenta("administrador")


@pytest.fixture()
def token(client, administrador):
    respuesta = client.post("/api/login", json={"correo": administrador.correo, "clave": CLAVE})
    return respuesta.get_json()["token"]


@pytest.fixture()
def pedir(client, token):
    """GET con el token del administrador. Uso: pedir("/api/facturas?desde=...")."""

    def get(url):
        return client.get(url, headers={"Authorization": f"Bearer {token}"})

    return get


@pytest.fixture()
def datos(app, administrador, crear_cuenta):
    """Una venta de cada estado, una compra y una venta fuera del rango de octubre."""
    estados_venta()
    vendedor = crear_cuenta("vendedor")
    cliente = Cliente(cedula="1098000001", nombres="Carlos Andrés", apellidos="Rueda Pinzón")
    proveedor = Proveedor(nit="900123456-7", nombre="Autopartes del Oriente S.A.S.")
    estados = {e.nombre: e for e in db.session.scalars(db.select(EstadoVenta))}

    def venta(fecha, total, estado="Completada"):
        return Venta(
            cliente=cliente, vendedor=vendedor, metodo_pago="Efectivo", total=Decimal(total), fecha=fecha,
            estado=estados[estado],
        )

    completada = venta(datetime(2026, 10, 30, 10, 15), "119000.00")
    db.session.add_all([
        completada,
        venta(datetime(2026, 10, 5, 9, 0), "50000.00", estado="Pendiente"),
        venta(datetime(2026, 10, 6, 9, 0), "70000.00", estado="Cancelada"),
        venta(datetime(2026, 11, 1, 0, 0), "10000.00"),
    ])
    compra = Compra(proveedor=proveedor, usuario=administrador, total=Decimal("675000.00"),
                    fecha=datetime(2026, 10, 4, 9, 30))
    db.session.add(compra)
    db.session.commit()
    return {"venta": completada, "compra": compra}


# ---------- Login ----------


def test_el_login_devuelve_un_token_bearer(client, administrador):
    respuesta = client.post("/api/login", json={"correo": administrador.correo, "clave": CLAVE})

    datos = respuesta.get_json()
    assert respuesta.status_code == 200
    assert datos["tipo"] == "Bearer"
    assert datos["token"]
    assert datos["expira_en"] == 8 * 3600
    assert datos["usuario"] == {"nombre": "Administrador", "rol": "administrador"}


def test_el_login_no_pide_token_csrf(app, client, administrador):
    app.config["WTF_CSRF_ENABLED"] = True

    respuesta = client.post("/api/login", json={"correo": administrador.correo, "clave": CLAVE})

    assert respuesta.status_code == 200


@pytest.mark.parametrize("clave", ["equivocada-1", ""])
def test_el_login_rechaza_una_clave_equivocada(client, administrador, clave):
    respuesta = client.post("/api/login", json={"correo": administrador.correo, "clave": clave})

    assert respuesta.status_code in (400, 401)
    assert "error" in respuesta.get_json()


@pytest.mark.parametrize("cuerpo", [None, "texto", {"correo": "admin@repuauto.com"}, {"correo": 1, "clave": 2}])
def test_el_login_pide_un_json_con_correo_y_clave(client, cuerpo):
    respuesta = client.post("/api/login", json=cuerpo) if cuerpo is not None else client.post("/api/login")

    assert respuesta.status_code == 400
    assert respuesta.get_json() == {"error": 'Envía un JSON con "correo" y "clave".'}


@pytest.mark.parametrize("rol", ["cliente", "vendedor"])
def test_solo_un_administrador_recibe_token(client, crear_cuenta, rol):
    usuario = crear_cuenta(rol)

    respuesta = client.post("/api/login", json={"correo": usuario.correo, "clave": CLAVE})

    assert respuesta.status_code == 403
    assert "token" not in respuesta.get_json()


def test_una_cuenta_desactivada_no_recibe_token(client, crear_cuenta):
    usuario = crear_cuenta("administrador", activo=False)

    respuesta = client.post("/api/login", json={"correo": usuario.correo, "clave": CLAVE})

    assert respuesta.status_code == 401


# ---------- Token ----------


def test_sin_token_la_api_responde_401_en_json(client):
    respuesta = client.get("/api/facturas")

    assert respuesta.status_code == 401
    assert respuesta.headers["WWW-Authenticate"].startswith("Bearer")
    assert "Authorization: Bearer" in respuesta.get_json()["error"]


def test_un_token_alterado_no_sirve(client, token):
    respuesta = client.get("/api/facturas", headers={"Authorization": f"Bearer {token}x"})

    assert respuesta.status_code == 401
    assert respuesta.get_json() == {"error": "El token no es válido."}


def test_un_token_vencido_no_sirve(app, client, token):
    app.config["API_TOKEN_HORAS"] = -1

    respuesta = client.get("/api/facturas", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 401
    assert "venció" in respuesta.get_json()["error"]


def test_un_token_firmado_con_otra_clave_no_sirve(client, administrador):
    falso = URLSafeTimedSerializer("otra-clave", salt="api-token").dumps({"id": administrador.id_usuario})

    respuesta = client.get("/api/facturas", headers={"Authorization": f"Bearer {falso}"})

    assert respuesta.status_code == 401


def test_si_desactivan_la_cuenta_su_token_deja_de_servir(pedir, administrador):
    administrador.activo = False
    db.session.commit()

    assert pedir("/api/facturas").status_code == 401


def test_la_sesion_del_navegador_no_reemplaza_el_token(client, administrador, iniciar_sesion):
    iniciar_sesion(administrador)

    assert client.get("/api/facturas").status_code == 401


# ---------- Facturas ----------


def test_las_facturas_siguen_el_formato_acordado(pedir, datos):
    respuesta = pedir("/api/facturas?desde=2026-10-01&hasta=2026-10-31")

    cuerpo = respuesta.get_json()
    assert respuesta.status_code == 200
    assert cuerpo["sucursal"] == "Bucaramanga"
    assert (cuerpo["desde"], cuerpo["hasta"], cuerpo["moneda"], cuerpo["iva_porcentaje"]) == (
        "2026-10-01", "2026-10-31", "COP", 19,
    )
    assert cuerpo["facturas"] == [
        {
            "tipo": "compra",
            "numero": f"C-{datos['compra'].id_compra:06d}",
            "fecha": "2026-10-04T09:30:00-05:00",
            "tercero": {"documento": "900123456-7", "nombre": "Autopartes del Oriente S.A.S."},
            "subtotal": "567226.89",
            "iva": "107773.11",
            "total": "675000.00",
        },
        {
            "tipo": "venta",
            "numero": f"V-{datos['venta'].id_venta:06d}",
            "fecha": "2026-10-30T10:15:00-05:00",
            "tercero": {"documento": "1098000001", "nombre": "Carlos Andrés Rueda Pinzón"},
            "subtotal": "100000.00",
            "iva": "19000.00",
            "total": "119000.00",
        },
    ]


def test_solo_van_las_ventas_completadas_del_rango(pedir, datos):
    cuerpo = pedir("/api/facturas?desde=2026-10-01&hasta=2026-10-31&tipo=venta").get_json()

    assert [f["total"] for f in cuerpo["facturas"]] == ["119000.00"]
    assert cuerpo["resumen"] == {
        "venta": {"cantidad": 1, "subtotal": "100000.00", "iva": "19000.00", "total": "119000.00"},
    }


def test_se_pueden_pedir_solo_las_compras(pedir, datos):
    cuerpo = pedir("/api/facturas?desde=2026-10-01&hasta=2026-10-31&tipo=compra").get_json()

    assert [f["tipo"] for f in cuerpo["facturas"]] == ["compra"]
    assert list(cuerpo["resumen"]) == ["compra"]


def test_el_resumen_suma_cada_tipo(pedir, datos):
    cuerpo = pedir("/api/facturas?desde=2026-10-01&hasta=2026-11-30").get_json()

    assert cuerpo["resumen"]["venta"]["cantidad"] == 2
    assert cuerpo["resumen"]["venta"]["total"] == "129000.00"
    assert cuerpo["resumen"]["compra"]["total"] == "675000.00"


def test_sin_facturas_la_lista_queda_vacia(pedir):
    cuerpo = pedir("/api/facturas?desde=2026-10-01&hasta=2026-10-31").get_json()

    assert cuerpo["facturas"] == []
    assert cuerpo["resumen"]["venta"] == {"cantidad": 0, "subtotal": "0.00", "iva": "0.00", "total": "0.00"}


@pytest.mark.parametrize("consulta, mensaje", [
    ("tipo=devolucion", 'El tipo debe ser "venta" o "compra"'),
    ("desde=2026-10-31&hasta=2026-10-01", "La fecha inicial no puede ir después"),
    ("desde=ayer", "AAAA-MM-DD"),
])
def test_los_parametros_invalidos_responden_400(pedir, consulta, mensaje):
    respuesta = pedir(f"/api/facturas?{consulta}")

    assert respuesta.status_code == 400
    assert mensaje in respuesta.get_json()["error"]


def test_la_sucursal_y_el_iva_salen_de_la_configuracion(app, pedir, datos):
    app.config["API_SUCURSAL"] = "Cali"
    app.config["API_IVA"] = 0

    cuerpo = pedir("/api/facturas?desde=2026-10-30&hasta=2026-10-30").get_json()

    assert cuerpo["sucursal"] == "Cali"
    assert cuerpo["facturas"][0]["subtotal"] == "119000.00"
    assert cuerpo["facturas"][0]["iva"] == "0.00"


# ---------- Cálculos y errores ----------


@pytest.mark.parametrize("total", ["0.00", "0.01", "1.00", "99999.99", "120000.00", "1234567.89"])
def test_subtotal_mas_iva_da_siempre_el_total(app, total):
    subtotal, iva = services.separar_iva(Decimal(total))

    assert subtotal + iva == Decimal(total)
    assert iva >= 0


def test_las_rutas_que_no_existen_responden_json(client):
    respuesta = client.get("/api/no-existe")

    assert respuesta.status_code == 404
    assert "error" in respuesta.get_json()


def test_un_metodo_no_permitido_responde_json(client):
    respuesta = client.get("/api/login")

    assert respuesta.status_code == 405
    assert "error" in respuesta.get_json()


def test_fuera_de_la_api_los_errores_siguen_siendo_html(client, administrador, iniciar_sesion):
    iniciar_sesion(administrador)

    respuesta = client.get("/no-existe")

    assert respuesta.status_code == 404
    assert respuesta.mimetype == "text/html"


# ---------- Inventario ----------


@pytest.fixture()
def repuestos(app):
    """Uno en stock, uno con stock bajo, uno agotado y uno desactivado."""
    frenos, filtros = Categoria(nombre="Frenos"), Categoria(nombre="Filtros")
    bosch = MarcaRepuesto(nombre="Bosch")

    def repuesto(codigo, nombre, categoria, stock, minimo, precio, activo=True):
        return Repuesto(codigo=codigo, nombre=nombre, categoria=categoria, marca=bosch, stock_actual=stock,
                        stock_minimo=minimo, precio_venta=Decimal(precio), activo=activo)

    db.session.add_all([
        repuesto("FRE-1", "Pastillas", frenos, 10, 4, "120000.00"),
        repuesto("FRE-2", "Disco", frenos, 2, 4, "185000.00"),
        repuesto("FIL-1", "Filtro de aceite", filtros, 0, 5, "28000.00"),
        repuesto("FIL-9", "Viejo", filtros, 50, 0, "1000.00", activo=False),
    ])
    db.session.commit()


def test_el_inventario_sigue_el_formato_acordado(pedir, repuestos):
    respuesta = pedir("/api/inventario")

    cuerpo = respuesta.get_json()
    assert respuesta.status_code == 200
    assert (cuerpo["sucursal"], cuerpo["moneda"]) == ("Bucaramanga", "COP")
    assert cuerpo["fecha"].endswith("-05:00")
    assert cuerpo["resumen"] == {
        "productos": 3, "unidades": 12, "valor": "1570000.00", "en_stock": 1, "stock_bajo": 1, "agotado": 1,
    }
    assert cuerpo["productos"][0] == {
        "codigo": "FIL-1", "nombre": "Filtro de aceite", "categoria": "Filtros", "marca": "Bosch",
        "stock": 0, "stock_minimo": 5, "precio_venta": "28000.00", "valor": "0.00", "estado": "agotado",
    }
    assert [p["codigo"] for p in cuerpo["productos"]] == ["FIL-1", "FRE-2", "FRE-1"]


def test_el_inventario_se_filtra_por_estado_sin_cambiar_el_resumen(pedir, repuestos):
    cuerpo = pedir("/api/inventario?estado=stock_bajo").get_json()

    assert [p["codigo"] for p in cuerpo["productos"]] == ["FRE-2"]
    assert cuerpo["resumen"]["productos"] == 3


def test_un_estado_que_no_existe_responde_400(pedir):
    respuesta = pedir("/api/inventario?estado=perdido")

    assert respuesta.status_code == 400
    assert "en_stock" in respuesta.get_json()["error"]


def test_el_inventario_pide_token(client):
    assert client.get("/api/inventario").status_code == 401
