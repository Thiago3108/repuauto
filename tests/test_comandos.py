"""Pruebas de los comandos de consola flask crear-admin y flask cambiar-clave."""
from app.auth import services as cuentas
from app.cli import roles


def test_crear_admin_crea_la_cuenta_con_rol_administrador(app):
    roles()
    resultado = app.test_cli_runner().invoke(
        args=["crear-admin", "Integracion@RepuAuto.com", "--nombre", "Integración UD1"],
        input="Clave-segura-1\nClave-segura-1\n",
    )

    usuario = cuentas.autenticar("integracion@repuauto.com", "Clave-segura-1")
    assert resultado.exit_code == 0, resultado.output
    assert usuario is not None
    assert usuario.tiene_rol("administrador")
    assert usuario.nombre == "Integración UD1"


def test_la_clave_no_se_muestra_en_pantalla(app):
    roles()
    resultado = app.test_cli_runner().invoke(
        args=["crear-admin", "integracion@repuauto.com"], input="Clave-segura-1\nClave-segura-1\n",
    )

    assert "Clave-segura-1" not in resultado.output


def test_crear_admin_rechaza_una_clave_debil(app):
    roles()
    resultado = app.test_cli_runner().invoke(
        args=["crear-admin", "integracion@repuauto.com", "--clave", "corta"],
    )

    assert resultado.exit_code != 0
    assert "carácter especial" in resultado.output
    assert cuentas.buscar_por_correo("integracion@repuauto.com") is None


def test_crear_admin_no_repite_correos(app, crear_cuenta):
    crear_cuenta("administrador", correo="integracion@repuauto.com")

    resultado = app.test_cli_runner().invoke(
        args=["crear-admin", "integracion@repuauto.com", "--clave", "Clave-segura-1"],
    )

    assert resultado.exit_code != 0
    assert "Ya existe" in resultado.output


def test_cambiar_clave_reemplaza_la_anterior(app, crear_cuenta):
    from tests.conftest import CLAVE

    usuario = crear_cuenta("administrador")

    resultado = app.test_cli_runner().invoke(
        args=["cambiar-clave", usuario.correo], input="Otra-clave-22\nOtra-clave-22\n",
    )

    assert resultado.exit_code == 0, resultado.output
    assert cuentas.autenticar(usuario.correo, "Otra-clave-22") is not None
    assert cuentas.autenticar(usuario.correo, CLAVE) is None


def test_cambiar_clave_avisa_si_el_correo_no_existe(app):
    resultado = app.test_cli_runner().invoke(
        args=["cambiar-clave", "nadie@repuauto.com", "--clave", "Clave-segura-1"],
    )

    assert resultado.exit_code != 0
    assert "No existe" in resultado.output
