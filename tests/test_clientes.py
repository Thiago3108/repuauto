"""Pruebas de US-02: tabla cliente, CRUD, búsqueda y enlace de cuentas (UI-08)."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Cliente, Usuario


def crear_cliente(cedula="1098765432", nombres="Ana María", apellidos="Rueda Gómez", **datos):
    cliente = Cliente(cedula=cedula, nombres=nombres, apellidos=apellidos, **datos)
    db.session.add(cliente)
    db.session.commit()
    return cliente


def test_un_cliente_de_mostrador_no_tiene_cuenta(app):
    cliente = crear_cliente()

    assert cliente.usuario is None
    assert cliente.telefono is None
    assert cliente.creado_en is not None
    assert cliente.nombre_completo == "Ana María Rueda Gómez"


def test_la_cedula_no_se_repite(app):
    crear_cliente(cedula="1098765432")

    with pytest.raises(IntegrityError):
        crear_cliente(cedula="1098765432")


def test_un_cliente_se_enlaza_con_su_cuenta(app, crear_cuenta):
    cuenta = crear_cuenta("cliente")

    cliente = crear_cliente(usuario=cuenta)

    assert cliente.id_usuario == cuenta.id_usuario
    assert cuenta.cliente is cliente


def test_una_cuenta_se_enlaza_a_un_solo_cliente(app, crear_cuenta):
    cuenta = crear_cuenta("cliente")
    crear_cliente(cedula="111", id_usuario=cuenta.id_usuario)

    with pytest.raises(IntegrityError):
        crear_cliente(cedula="222", id_usuario=cuenta.id_usuario)


# ---------- CRUD de clientes (UI-08) ----------


@pytest.fixture()
def como_vendedor(crear_cuenta, iniciar_sesion):
    iniciar_sesion(crear_cuenta("vendedor"))


def datos_cliente(**cambios):
    datos = {"cedula": "1098765432", "nombres": "Ana María", "apellidos": "Rueda Gómez", "telefono": "3001234567"}
    datos.update(cambios)
    return datos


def test_la_lista_sin_clientes(client, como_vendedor):
    pagina = client.get("/clientes/").get_data(as_text=True)

    assert "Todavía no hay clientes" in pagina


def test_la_lista_muestra_los_clientes_ordenados_por_apellido(client, como_vendedor):
    crear_cliente(cedula="1", nombres="Zoe", apellidos="Zapata")
    crear_cliente(cedula="2", nombres="Ana", apellidos="Álvarez")

    pagina = client.get("/clientes/").get_data(as_text=True)

    assert "2 clientes registrados" in pagina
    assert pagina.index("Álvarez") < pagina.index("Zapata")


def test_la_lista_se_divide_en_paginas(client, como_vendedor):
    for numero in range(25):
        db.session.add(Cliente(cedula=str(1000 + numero), nombres="Cliente", apellidos=f"Apellido {numero:02d}"))
    db.session.commit()

    primera = client.get("/clientes/").get_data(as_text=True)
    segunda = client.get("/clientes/?pagina=2").get_data(as_text=True)

    assert "Apellido 00" in primera and "Apellido 24" not in primera
    assert "Apellido 24" in segunda


def test_crear_un_cliente_de_mostrador(client, como_vendedor):
    respuesta = client.post("/clientes/nuevo", data=datos_cliente(nombres="  Ana   María "), follow_redirects=True)

    assert "Se registró a Ana María Rueda Gómez." in respuesta.get_data(as_text=True)
    cliente = db.session.scalar(db.select(Cliente))
    assert cliente.nombres == "Ana María"
    assert cliente.usuario is None


def test_el_telefono_es_opcional(client, como_vendedor):
    client.post("/clientes/nuevo", data=datos_cliente(telefono=""))

    assert db.session.scalar(db.select(Cliente)).telefono is None


def test_si_la_cedula_ya_existe_se_muestra_ese_cliente(client, como_vendedor):
    existente = crear_cliente(cedula="1098765432")

    respuesta = client.post("/clientes/nuevo", data=datos_cliente(nombres="Otro"))

    assert respuesta.headers["Location"] == f"/clientes/{existente.id_cliente}"
    pagina = client.get(respuesta.headers["Location"]).get_data(as_text=True)
    assert "Ya existe un cliente con la cédula 1098765432" in pagina
    assert len(db.session.scalars(db.select(Cliente)).all()) == 1


@pytest.mark.parametrize("cambio, mensaje", [
    ({"cedula": ""}, "Escribe la cédula."),
    ({"cedula": "10.987.654"}, "Usa solo números"),
    ({"nombres": "Ana2"}, "Usa solo letras y espacios."),
    ({"apellidos": ""}, "Escribe los apellidos."),
    ({"telefono": "300-123"}, "Usa solo números"),
])
def test_validaciones_del_cliente(client, como_vendedor, cambio, mensaje):
    respuesta = client.post("/clientes/nuevo", data=datos_cliente(**cambio))

    assert respuesta.status_code == 200
    assert mensaje in respuesta.get_data(as_text=True)
    assert db.session.scalar(db.select(Cliente)) is None


def test_el_detalle_muestra_los_datos_y_la_cuenta(client, crear_cuenta, como_vendedor):
    cuenta = crear_cuenta("cliente", correo="ana@correo.com")
    cliente = crear_cliente(usuario=cuenta, telefono="3001234567")

    pagina = client.get(f"/clientes/{cliente.id_cliente}").get_data(as_text=True)

    assert "Ana María Rueda Gómez" in pagina
    assert "3001234567" in pagina
    assert "ana@correo.com" in pagina


def test_un_cliente_que_no_existe_da_404(client, como_vendedor):
    assert client.get("/clientes/999").status_code == 404
    assert client.get("/clientes/999/editar").status_code == 404


def test_editar_un_cliente(client, como_vendedor):
    cliente = crear_cliente()

    respuesta = client.post(
        f"/clientes/{cliente.id_cliente}/editar",
        data=datos_cliente(apellidos="Rueda Pérez", telefono=""),
        follow_redirects=True,
    )

    assert "Se guardaron los cambios." in respuesta.get_data(as_text=True)
    db.session.refresh(cliente)
    assert cliente.apellidos == "Rueda Pérez"
    assert cliente.telefono is None


def test_el_formulario_de_edicion_trae_los_datos_actuales(client, como_vendedor):
    cliente = crear_cliente()

    pagina = client.get(f"/clientes/{cliente.id_cliente}/editar").get_data(as_text=True)

    assert 'value="1098765432"' in pagina
    assert 'value="Ana María"' in pagina


def test_al_editar_no_se_puede_usar_la_cedula_de_otro(client, como_vendedor):
    crear_cliente(cedula="111")
    segundo = crear_cliente(cedula="222")

    respuesta = client.post(f"/clientes/{segundo.id_cliente}/editar", data=datos_cliente(cedula="111"))

    assert "Esta cédula ya es de Ana María Rueda Gómez." in respuesta.get_data(as_text=True)
    db.session.refresh(segundo)
    assert segundo.cedula == "222"


def test_al_editar_se_puede_dejar_la_misma_cedula(client, como_vendedor):
    cliente = crear_cliente(cedula="111")

    respuesta = client.post(f"/clientes/{cliente.id_cliente}/editar", data=datos_cliente(cedula="111"))

    assert respuesta.status_code == 302


@pytest.mark.parametrize("rol, codigo", [("cliente", 403), ("vendedor", 200), ("administrador", 200)])
def test_solo_el_personal_gestiona_clientes(client, crear_cuenta, iniciar_sesion, rol, codigo):
    iniciar_sesion(crear_cuenta(rol))
    cliente = crear_cliente()

    assert client.get("/clientes/").status_code == codigo
    assert client.get("/clientes/nuevo").status_code == codigo
    assert client.get(f"/clientes/{cliente.id_cliente}").status_code == codigo
    assert client.get(f"/clientes/{cliente.id_cliente}/editar").status_code == codigo


# ---------- Búsqueda de clientes (US-02 T3) ----------


@pytest.fixture()
def tres_clientes(app):
    crear_cliente(cedula="1098765432", nombres="Ana María", apellidos="Rueda Gómez", telefono="3001234567")
    crear_cliente(cedula="91234567", nombres="Pedro", apellidos="Pérez Ruiz", telefono="3159876543")
    crear_cliente(cedula="63111222", nombres="Lucía", apellidos="Ñañez", telefono=None)


def nombres_en(pagina):
    return [nombre for nombre in ("Ana María", "Pedro", "Lucía") if nombre in pagina]


@pytest.mark.parametrize("busqueda, esperados", [
    ("1098765432", ["Ana María"]),     # cédula completa
    ("9123", ["Pedro"]),               # parte de la cédula
    ("rue", ["Ana María"]),            # parte del apellido
    ("PEDRO", ["Pedro"]),              # sin importar mayúsculas
    ("gomez", ["Ana María"]),          # sin importar tildes
    ("nanez", ["Lucía"]),              # ñ sin tilde
    ("315987", ["Pedro"]),             # parte del teléfono
    ("ana rueda", ["Ana María"]),      # varias palabras, en campos distintos
    ("r", ["Ana María", "Pedro"]),     # coinciden varios
    ("ana pérez", []),                 # cada palabra tiene que aparecer
    ("zzz", []),
])
def test_buscar_clientes(client, como_vendedor, tres_clientes, busqueda, esperados):
    pagina = client.get("/clientes/", query_string={"q": busqueda}).get_data(as_text=True)

    assert nombres_en(pagina) == esperados


def test_la_busqueda_dice_cuantos_resultados_hay(client, como_vendedor, tres_clientes):
    pagina = client.get("/clientes/?q=r").get_data(as_text=True)

    assert "2 resultados para «r»" in pagina
    assert 'value="r"' in pagina


def test_sin_resultados_ofrece_registrar_al_cliente(client, como_vendedor, tres_clientes):
    pagina = client.get("/clientes/?q=zzz").get_data(as_text=True)

    assert "No hay clientes que coincidan con «zzz»" in pagina
    assert "/clientes/nuevo" in pagina


def test_una_busqueda_vacia_muestra_todos(client, como_vendedor, tres_clientes):
    pagina = client.get("/clientes/?q=+++").get_data(as_text=True)

    assert nombres_en(pagina) == ["Ana María", "Pedro", "Lucía"]


@pytest.mark.parametrize("busqueda", ["%", "_", "\\"])
def test_los_simbolos_se_buscan_como_texto(client, como_vendedor, tres_clientes, busqueda):
    pagina = client.get("/clientes/", query_string={"q": busqueda}).get_data(as_text=True)

    assert nombres_en(pagina) == []


def test_la_busqueda_se_conserva_al_cambiar_de_pagina(client, como_vendedor):
    for numero in range(25):
        db.session.add(Cliente(cedula=str(5000 + numero), nombres="Carlos", apellidos=f"Apellido {numero:02d}"))
    db.session.add(Cliente(cedula="777", nombres="Otro", apellidos="Distinto"))
    db.session.commit()

    primera = client.get("/clientes/?q=carlos").get_data(as_text=True)
    segunda = client.get("/clientes/?q=carlos&pagina=2").get_data(as_text=True)

    assert "pagina=2&amp;q=carlos" in primera or "q=carlos&amp;pagina=2" in primera
    assert "Apellido 24" in segunda
    assert "Distinto" not in segunda


# ---------- Enlazar la cuenta de un cliente (US-02 T4) ----------


def enlazar(client, cliente, cuenta, verificado=True):
    datos = {"id_usuario": cuenta.id_usuario}
    if verificado:
        datos["verificado"] = "y"
    return client.post(f"/clientes/{cliente.id_cliente}/enlazar", data=datos, follow_redirects=True)


def test_buscar_la_cuenta_por_correo(client, crear_cuenta, como_vendedor):
    crear_cuenta("cliente", correo="ana.rueda@correo.com")
    crear_cuenta("cliente", correo="pedro@correo.com")
    cliente = crear_cliente()

    pagina = client.get(f"/clientes/{cliente.id_cliente}/enlazar?correo=ANA").get_data(as_text=True)

    assert "ana.rueda@correo.com" in pagina
    assert "pedro@correo.com" not in pagina


def test_solo_aparecen_cuentas_de_cliente_activas_y_sin_enlazar(client, crear_cuenta, como_vendedor):
    crear_cuenta("cliente", correo="libre@correo.com")
    crear_cuenta("cliente", correo="inactiva@correo.com", activo=False)
    crear_cuenta("vendedor", correo="vendedor2@correo.com")
    crear_cliente(cedula="111", usuario=crear_cuenta("cliente", correo="enlazada@correo.com"))
    cliente = crear_cliente(cedula="222")

    pagina = client.get(f"/clientes/{cliente.id_cliente}/enlazar?correo=correo.com").get_data(as_text=True)

    assert "libre@correo.com" in pagina
    for correo in ("inactiva@correo.com", "vendedor2@correo.com", "enlazada@correo.com"):
        assert correo not in pagina


def test_enlazar_una_cuenta_verificando_la_cedula(client, crear_cuenta, como_vendedor):
    cuenta = crear_cuenta("cliente", correo="ana@correo.com")
    cliente = crear_cliente()

    respuesta = enlazar(client, cliente, cuenta)

    assert "Se enlazó la cuenta ana@correo.com con Ana María Rueda Gómez." in respuesta.get_data(as_text=True)
    db.session.refresh(cliente)
    assert cliente.usuario is cuenta


def test_sin_confirmar_la_verificacion_no_se_enlaza(client, crear_cuenta, como_vendedor):
    cuenta = crear_cuenta("cliente")
    cliente = crear_cliente()

    respuesta = enlazar(client, cliente, cuenta, verificado=False)

    assert "Confirma que verificaste la cédula en persona." in respuesta.get_data(as_text=True)
    db.session.refresh(cliente)
    assert cliente.usuario is None


def test_una_cuenta_se_enlaza_a_un_solo_cliente_desde_la_vista(client, crear_cuenta, como_vendedor):
    cuenta = crear_cuenta("cliente")
    primero = crear_cliente(cedula="111", nombres="Primero")
    segundo = crear_cliente(cedula="222")
    enlazar(client, primero, cuenta)

    respuesta = enlazar(client, segundo, cuenta)

    assert "Esa cuenta ya está enlazada con Primero Rueda Gómez." in respuesta.get_data(as_text=True)
    db.session.refresh(segundo)
    assert segundo.usuario is None


def test_no_se_enlaza_una_cuenta_que_no_es_de_cliente(client, crear_cuenta, como_vendedor):
    vendedor = crear_cuenta("vendedor", correo="otro.vendedor@correo.com")
    cliente = crear_cliente()

    respuesta = enlazar(client, cliente, vendedor)

    assert "no es una cuenta de cliente activa" in respuesta.get_data(as_text=True)
    db.session.refresh(cliente)
    assert cliente.usuario is None


def test_un_cliente_con_cuenta_no_se_vuelve_a_enlazar(client, crear_cuenta, como_vendedor):
    cliente = crear_cliente(usuario=crear_cuenta("cliente", correo="ana@correo.com"))

    respuesta = client.get(f"/clientes/{cliente.id_cliente}/enlazar")

    assert respuesta.headers["Location"] == f"/clientes/{cliente.id_cliente}"


def test_el_cliente_enlazado_ve_su_cuenta_y_puede_quitarse_el_enlace(client, crear_cuenta, como_vendedor):
    cuenta = crear_cuenta("cliente", correo="ana@correo.com")
    cliente = crear_cliente(usuario=cuenta)

    pagina = client.post(f"/clientes/{cliente.id_cliente}/quitar-enlace", follow_redirects=True).get_data(as_text=True)

    assert "Se quitó el enlace con la cuenta ana@correo.com." in pagina
    db.session.refresh(cliente)
    assert cliente.usuario is None
    assert db.session.get(Usuario, cuenta.id_usuario) is not None


def test_el_registro_de_un_cliente_de_mostrador_se_puede_enlazar_despues(client, crear_cuenta, iniciar_sesion):
    """Flujo completo: cliente de mostrador → se registra (sin enlazar) → el vendedor lo enlaza."""
    cliente = crear_cliente(cedula="1098765432")
    vendedor = crear_cuenta("vendedor")
    client.post("/auth/registro", data={
        "nombres": "Ana María", "apellidos": "Rueda Gómez", "cedula": "1098765432", "telefono": "",
        "correo": "ana@correo.com", "clave": "clave-segura-1", "confirmar": "clave-segura-1",
    })
    client.post("/auth/logout")
    iniciar_sesion(vendedor)
    cuenta = db.session.scalar(db.select(Usuario).filter_by(correo="ana@correo.com"))

    enlazar(client, cliente, cuenta)

    db.session.refresh(cliente)
    assert cliente.usuario.correo == "ana@correo.com"


@pytest.mark.parametrize("rol, codigo", [("cliente", 403), ("vendedor", 200), ("administrador", 200)])
def test_solo_el_personal_enlaza_cuentas(client, crear_cuenta, iniciar_sesion, rol, codigo):
    iniciar_sesion(crear_cuenta(rol))
    cliente = crear_cliente()

    assert client.get(f"/clientes/{cliente.id_cliente}/enlazar").status_code == codigo
