"""Pruebas de US-01: tablas, semillas, inicio de sesión y control de acceso por rol."""
import pytest
from flask import Blueprint
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from app.auth.decoradores import rol_requerido
from app.auth.services import contrasena_segura
from app.cli import primer_administrador, roles
from app.extensions import db
from app.models import Cliente, Rol, Usuario


def crear_usuario(correo="ana@correo.com", rol="cliente"):
    usuario = Usuario(
        correo=correo,
        contrasena_hash="hash-de-prueba",
        nombre="Ana",
        rol=Rol(nombre=rol),
    )
    db.session.add(usuario)
    db.session.commit()
    return usuario


def test_la_semilla_crea_los_tres_roles_sin_duplicar(app):
    roles()
    roles()
    db.session.commit()

    nombres = db.session.scalars(db.select(Rol.nombre)).all()
    assert sorted(nombres) == ["administrador", "cliente", "vendedor"]


def test_un_usuario_nuevo_queda_activo_y_con_fecha(app):
    usuario = crear_usuario()

    assert usuario.activo is True
    assert usuario.creado_en is not None
    assert usuario.rol.nombre == "cliente"


def test_el_correo_no_se_repite(app):
    crear_usuario(correo="ana@correo.com", rol="cliente")

    with pytest.raises(IntegrityError):
        crear_usuario(correo="ana@correo.com", rol="vendedor")


def test_el_nombre_del_rol_no_se_repite(app):
    db.session.add(Rol(nombre="cliente"))
    db.session.commit()

    db.session.add(Rol(nombre="cliente"))
    with pytest.raises(IntegrityError):
        db.session.commit()


# ---------- Primer administrador (flask seed) ----------


def test_la_semilla_crea_el_administrador_una_sola_vez(app, monkeypatch):
    monkeypatch.setenv("ADMIN_CORREO", "Admin@RepuAuto.com ")
    monkeypatch.setenv("ADMIN_CLAVE", "clave-segura-1")
    for _ in range(2):
        roles()
        primer_administrador()
        db.session.commit()

    administradores = db.session.scalars(db.select(Usuario)).all()
    assert len(administradores) == 1
    assert administradores[0].correo == "admin@repuauto.com"
    assert administradores[0].rol.nombre == "administrador"
    assert administradores[0].contrasena_hash != "clave-segura-1"


def test_la_semilla_rechaza_una_clave_debil(app, monkeypatch):
    monkeypatch.setenv("ADMIN_CORREO", "admin@repuauto.com")
    monkeypatch.setenv("ADMIN_CLAVE", "123456789")
    roles()

    with pytest.raises(Exception, match="ADMIN_CLAVE"):
        primer_administrador()


@pytest.mark.parametrize(
    "clave, segura",
    [
        ("clave-segura-1", True),
        ("corta-1", False),         # 7 caracteres
        ("ocho-ch1", False),        # 8: tiene que tener más de 8
        ("sin-numeros", False),
        ("sinespecial1", False),
    ],
)
def test_reglas_de_la_contrasena(clave, segura):
    assert contrasena_segura(clave) is segura


# ---------- Inicio de sesión (UI-01) ----------


def test_sin_sesion_cualquier_pagina_lleva_al_login(client):
    respuesta = client.get("/clientes/")

    assert respuesta.status_code == 302
    assert "/auth/login" in respuesta.headers["Location"]


def test_login_correcto_entra_al_inicio(client, crear_cuenta, iniciar_sesion):
    vendedor = crear_cuenta("vendedor")

    respuesta = iniciar_sesion(vendedor)

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"] == "/"
    assert "Hola, Vendedor" in client.get("/").get_data(as_text=True)


def test_el_correo_no_distingue_mayusculas(client, crear_cuenta):
    crear_cuenta("cliente", correo="ana@correo.com")

    respuesta = client.post("/auth/login", data={"correo": " ANA@correo.com", "clave": "clave-segura-1"})

    assert respuesta.status_code == 302


@pytest.mark.parametrize("correo, clave", [
    ("cliente@repuauto.com", "clave-equivocada-1"),
    ("nadie@repuauto.com", "clave-segura-1"),
])
def test_login_fallido_muestra_un_mensaje_generico(client, crear_cuenta, correo, clave):
    crear_cuenta("cliente")

    respuesta = client.post("/auth/login", data={"correo": correo, "clave": clave})

    assert respuesta.status_code == 200
    assert "Correo o contraseña incorrectos." in respuesta.get_data(as_text=True)


def test_una_cuenta_desactivada_no_entra(client, crear_cuenta, iniciar_sesion):
    desactivada = crear_cuenta("vendedor", activo=False)

    respuesta = iniciar_sesion(desactivada)

    assert "Correo o contraseña incorrectos." in respuesta.get_data(as_text=True)


def test_si_desactivan_la_cuenta_pierde_la_sesion(client, crear_cuenta, iniciar_sesion):
    vendedor = crear_cuenta("vendedor")
    iniciar_sesion(vendedor)
    vendedor.activo = False
    db.session.commit()

    assert client.get("/").status_code == 302


def test_despues_del_login_vuelve_a_la_pagina_pedida(client, crear_cuenta):
    crear_cuenta("vendedor")

    respuesta = client.post(
        "/auth/login?next=/clientes/",
        data={"correo": "vendedor@repuauto.com", "clave": "clave-segura-1"},
    )

    assert respuesta.headers["Location"] == "/clientes/"


def test_no_redirige_a_otro_sitio_despues_del_login(client, crear_cuenta):
    crear_cuenta("vendedor")

    respuesta = client.post(
        "/auth/login?next=//sitio-malo.com",
        data={"correo": "vendedor@repuauto.com", "clave": "clave-segura-1"},
    )

    assert respuesta.headers["Location"] == "/"


def test_cerrar_sesion(client, crear_cuenta, iniciar_sesion):
    iniciar_sesion(crear_cuenta("cliente"))

    with client:
        client.post("/auth/logout")
        assert not current_user.is_authenticated
    assert client.get("/").status_code == 302


# ---------- Control de acceso por rol ----------


@pytest.mark.parametrize("rol, ve, no_ve", [
    ("cliente", {"Catálogo"}, {"Ventas", "Clientes", "Reportes", "Cuentas y acceso"}),
    ("vendedor", {"Catálogo", "Ventas", "Clientes", "Repuestos y stock"}, {"Vehículos", "Reportes"}),
    ("administrador", {"Catálogo", "Ventas", "Reportes", "Cuentas y acceso"}, set()),
])
def test_cada_rol_ve_solo_su_menu(client, crear_cuenta, iniciar_sesion, rol, ve, no_ve):
    iniciar_sesion(crear_cuenta(rol))

    pagina = client.get("/").get_data(as_text=True)

    assert all(texto in pagina for texto in ve)
    assert not any(texto in pagina for texto in no_ve)


@pytest.mark.parametrize("rol, codigo", [("cliente", 403), ("vendedor", 403), ("administrador", 200)])
def test_cuentas_y_acceso_es_solo_del_administrador(client, crear_cuenta, iniciar_sesion, rol, codigo):
    iniciar_sesion(crear_cuenta(rol))

    assert client.get("/auth/").status_code == codigo


def test_rol_requerido_protege_la_vista_de_otro_modulo(app, crear_cuenta):
    """Así protegerá cada integrante sus vistas."""
    prueba = Blueprint("prueba", __name__)

    @prueba.get("/solo-personal")
    @rol_requerido("vendedor", "administrador")
    def solo_personal():
        return "ok"

    app.register_blueprint(prueba)
    client = app.test_client()
    client.post("/auth/login", data={"correo": crear_cuenta("cliente").correo, "clave": "clave-segura-1"})
    assert client.get("/solo-personal").status_code == 403

    client.post("/auth/logout")
    client.post("/auth/login", data={"correo": crear_cuenta("vendedor").correo, "clave": "clave-segura-1"})
    assert client.get("/solo-personal").status_code == 200


# ---------- Registro de cliente (UI-02) ----------


@pytest.fixture()
def con_roles(app):
    roles()
    db.session.commit()


def datos_registro(**cambios):
    datos = {
        "nombres": "Ana María",
        "apellidos": "Rueda Gómez",
        "cedula": "1098765432",
        "telefono": "3001234567",
        "correo": "ana@correo.com",
        "clave": "clave-segura-1",
        "confirmar": "clave-segura-1",
    }
    datos.update(cambios)
    return datos


def test_el_registro_se_abre_sin_sesion(client):
    assert client.get("/auth/registro").status_code == 200


def test_registro_crea_la_cuenta_y_el_cliente_enlazados(client, con_roles):
    respuesta = client.post("/auth/registro", data=datos_registro(correo=" Ana@Correo.com "))

    assert respuesta.status_code == 302
    usuario = db.session.scalar(db.select(Usuario))
    assert usuario.correo == "ana@correo.com"
    assert usuario.rol.nombre == "cliente"
    assert usuario.nombre == "Ana María Rueda Gómez"
    assert usuario.contrasena_hash != "clave-segura-1"
    assert usuario.cliente.cedula == "1098765432"
    assert usuario.cliente.telefono == "3001234567"
    # Queda con la sesión iniciada.
    assert "Hola, Ana María" in client.get("/").get_data(as_text=True)


def test_registro_limpia_los_espacios(client, con_roles):
    client.post("/auth/registro", data=datos_registro(nombres="  Ana   María ", cedula=" 1098765432 "))

    cliente = db.session.scalar(db.select(Cliente))
    assert cliente.nombres == "Ana María"
    assert cliente.cedula == "1098765432"


def test_el_telefono_es_opcional(client, con_roles):
    client.post("/auth/registro", data=datos_registro(telefono=""))

    assert db.session.scalar(db.select(Cliente)).telefono is None


def test_cliente_de_mostrador_crea_la_cuenta_sin_enlazar(client, con_roles):
    db.session.add(Cliente(cedula="1098765432", nombres="Ana", apellidos="Rueda"))
    db.session.commit()

    respuesta = client.post("/auth/registro", data=datos_registro(), follow_redirects=True)

    assert "Un vendedor enlazará tu cuenta" in respuesta.get_data(as_text=True)
    cliente = db.session.scalar(db.select(Cliente))
    assert cliente.id_usuario is None
    assert db.session.scalar(db.select(Usuario).filter_by(correo="ana@correo.com")) is not None
    assert len(db.session.scalars(db.select(Cliente)).all()) == 1


def test_no_se_repite_el_correo(client, con_roles, crear_cuenta):
    crear_cuenta("cliente", correo="ana@correo.com")

    respuesta = client.post("/auth/registro", data=datos_registro())

    assert "Ya existe una cuenta con este correo." in respuesta.get_data(as_text=True)
    assert db.session.scalar(db.select(Cliente)) is None


def test_una_cedula_con_cuenta_no_se_registra_otra_vez(client, con_roles):
    client.post("/auth/registro", data=datos_registro())
    client.post("/auth/logout")

    respuesta = client.post("/auth/registro", data=datos_registro(correo="otra@correo.com"))

    assert "Ya existe una cuenta con esta cédula." in respuesta.get_data(as_text=True)
    assert len(db.session.scalars(db.select(Usuario)).all()) == 1


@pytest.mark.parametrize("cambio, mensaje", [
    ({"nombres": "Ana2"}, "Usa solo letras y espacios."),
    ({"apellidos": "Rueda-Gómez"}, "Usa solo letras y espacios."),
    ({"cedula": "10.987.654"}, "Usa solo números"),
    ({"telefono": "300 123 abc"}, "Usa solo números"),
    ({"correo": "ana-sin-arroba.com"}, "Escribe un correo válido"),
    ({"clave": "corta-1", "confirmar": "corta-1"}, "más de 8 caracteres"),
    ({"clave": "sin-numeros", "confirmar": "sin-numeros"}, "más de 8 caracteres"),
    ({"confirmar": "otra-clave-1"}, "Las contraseñas no coinciden."),
    ({"nombres": ""}, "Escribe tus nombres."),
])
def test_validaciones_del_registro(client, con_roles, cambio, mensaje):
    respuesta = client.post("/auth/registro", data=datos_registro(**cambio))

    assert respuesta.status_code == 200
    assert mensaje in respuesta.get_data(as_text=True)
    assert db.session.scalar(db.select(Usuario)) is None


def test_con_sesion_iniciada_el_registro_lleva_al_inicio(client, crear_cuenta, iniciar_sesion):
    iniciar_sesion(crear_cuenta("vendedor"))

    assert client.get("/auth/registro").headers["Location"] == "/"


# ---------- Cuentas de vendedor (UI-13) ----------


def datos_vendedor(**cambios):
    datos = {
        "nombre": "Pedro Pérez",
        "correo": "pedro@repuauto.com",
        "clave": "clave-segura-1",
        "confirmar": "clave-segura-1",
    }
    datos.update(cambios)
    return datos


@pytest.fixture()
def como_administrador(crear_cuenta, iniciar_sesion):
    iniciar_sesion(crear_cuenta("administrador"))


def test_el_administrador_crea_un_vendedor(client, como_administrador):
    respuesta = client.post("/auth/", data=datos_vendedor(correo=" Pedro@RepuAuto.com "), follow_redirects=True)

    pagina = respuesta.get_data(as_text=True)
    assert "Se creó la cuenta de Pedro Pérez" in pagina
    assert "pedro@repuauto.com" in pagina
    vendedor = db.session.scalar(db.select(Usuario).filter_by(correo="pedro@repuauto.com"))
    assert vendedor.rol.nombre == "vendedor"
    assert vendedor.activo is True
    assert vendedor.contrasena_hash != "clave-segura-1"


def test_el_vendedor_nuevo_puede_iniciar_sesion(client, como_administrador):
    client.post("/auth/", data=datos_vendedor())
    client.post("/auth/logout")

    respuesta = client.post("/auth/login", data={"correo": "pedro@repuauto.com", "clave": "clave-segura-1"})

    assert respuesta.status_code == 302
    assert "Pedro Pérez · Vendedor" in client.get("/").get_data(as_text=True)


def test_no_se_crea_un_vendedor_con_un_correo_repetido(client, crear_cuenta, como_administrador):
    crear_cuenta("cliente", correo="pedro@repuauto.com")

    respuesta = client.post("/auth/", data=datos_vendedor())

    assert "Ya existe una cuenta con este correo." in respuesta.get_data(as_text=True)
    assert db.session.scalars(db.select(Usuario).join(Usuario.rol).filter(Rol.nombre == "vendedor")).all() == []


@pytest.mark.parametrize("cambio, mensaje", [
    ({"nombre": "Pedro 2"}, "Usa solo letras y espacios."),
    ({"correo": "pedro.com"}, "Escribe un correo válido"),
    ({"clave": "debil", "confirmar": "debil"}, "más de 8 caracteres"),
    ({"confirmar": "otra-clave-1"}, "Las contraseñas no coinciden."),
])
def test_validaciones_de_la_cuenta_de_vendedor(client, como_administrador, cambio, mensaje):
    respuesta = client.post("/auth/", data=datos_vendedor(**cambio))

    assert mensaje in respuesta.get_data(as_text=True)
    assert db.session.scalar(db.select(Usuario).filter_by(correo="pedro@repuauto.com")) is None


def test_desactivar_y_reactivar_un_vendedor(client, crear_cuenta, como_administrador):
    vendedor = crear_cuenta("vendedor")

    client.post(f"/auth/vendedores/{vendedor.id_usuario}/estado", data={"activo": "0"})
    db.session.refresh(vendedor)
    assert vendedor.activo is False

    client.post(f"/auth/vendedores/{vendedor.id_usuario}/estado", data={"activo": "1"})
    db.session.refresh(vendedor)
    assert vendedor.activo is True


def test_un_vendedor_desactivado_no_inicia_sesion(client, crear_cuenta, como_administrador):
    vendedor = crear_cuenta("vendedor")
    client.post(f"/auth/vendedores/{vendedor.id_usuario}/estado", data={"activo": "0"})
    client.post("/auth/logout")

    respuesta = client.post("/auth/login", data={"correo": vendedor.correo, "clave": "clave-segura-1"})

    assert "Correo o contraseña incorrectos." in respuesta.get_data(as_text=True)


def test_solo_se_desactivan_cuentas_de_vendedor(client, crear_cuenta, como_administrador):
    cliente = crear_cuenta("cliente")

    respuesta = client.post(f"/auth/vendedores/{cliente.id_usuario}/estado", data={"activo": "0"})

    assert respuesta.status_code == 404
    db.session.refresh(cliente)
    assert cliente.activo is True


@pytest.mark.parametrize("rol", ["cliente", "vendedor"])
def test_solo_el_administrador_crea_o_desactiva_vendedores(client, crear_cuenta, iniciar_sesion, rol):
    otro = crear_cuenta("vendedor", correo="otro@repuauto.com")
    iniciar_sesion(crear_cuenta(rol))

    assert client.post("/auth/", data=datos_vendedor()).status_code == 403
    assert client.post(f"/auth/vendedores/{otro.id_usuario}/estado", data={"activo": "0"}).status_code == 403
    assert db.session.scalar(db.select(Usuario).filter_by(correo="pedro@repuauto.com")) is None
