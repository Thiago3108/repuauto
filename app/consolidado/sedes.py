"""Conexión con la API de la otra sede y traducción de sus datos al formato común.

El formato común es el de nuestra API (docs/API.md): cada factura trae tipo, numero,
fecha, tercero (documento y nombre), subtotal, iva y total.

La otra sede se configura en el .env (SEDE_REMOTA_*). Hay dos tipos:
- "ud1": la API en Django REST del grupo UD1, tal como está hoy. Se piden sus ventas,
  clientes, lotes de compra y proveedores, y se traducen aquí.
- "repuauto": una API con nuestro mismo formato (GET /api/facturas). Sirve si UD1
  implementa el formato acordado, o para probar con otra copia de RepuAuto.

La URL puede ser local (http://127.0.0.1:8000/api) o pública con ngrok
(https://xxxx.ngrok-free.app/api).
"""
import json
import time as reloj
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from urllib import error as url_error
from urllib import parse, request

from flask import current_app

from app.api.services import HORA_COLOMBIA, _texto, fecha_iso, separar_iva

ESPERA_SEGUNDOS = 10
# El JWT de UD1 dura 5 minutos y su login acepta 10 intentos por minuto: el token se
# guarda 4 minutos para no iniciar sesión en cada recarga de la página.
TOKEN_SEGUNDOS = 4 * 60
_tokens = {}


class SedeNoDisponible(Exception):
    """No se pudieron traer los datos de la otra sede. mensaje explica por qué."""

    def __init__(self, mensaje):
        super().__init__(mensaje)
        self.mensaje = mensaje


def configurada():
    return bool(current_app.config.get("SEDE_REMOTA_URL"))


def nombre_remota():
    return current_app.config.get("SEDE_REMOTA_NOMBRE") or "Otra sede"


def facturas_remotas(desde, hasta):
    """Facturas de la otra sede entre dos fechas, en el formato común.

    Lanza SedeNoDisponible si no está configurada, no responde, rechaza el usuario o
    devuelve algo que no se entiende.
    """
    if not configurada():
        raise SedeNoDisponible("La otra sede no está configurada (SEDE_REMOTA_URL en el .env).")
    tipo = current_app.config.get("SEDE_REMOTA_TIPO", "ud1")
    try:
        if tipo == "repuauto":
            return _desde_repuauto(desde, hasta)
        if tipo == "ud1":
            return _desde_ud1(desde, hasta)
    except (KeyError, TypeError, ValueError, InvalidOperation) as dato_raro:
        raise SedeNoDisponible(f"La otra sede respondió datos que no se entienden ({dato_raro}).")
    raise SedeNoDisponible(f'SEDE_REMOTA_TIPO debe ser "ud1" o "repuauto", no "{tipo}".')


# ---------- API con nuestro formato ----------


def _desde_repuauto(desde, hasta):
    token = _pedir("POST", "/login", {
        "correo": current_app.config["SEDE_REMOTA_USUARIO"],
        "clave": current_app.config["SEDE_REMOTA_CLAVE"],
    })["token"]
    consulta = parse.urlencode({"desde": desde.isoformat(), "hasta": hasta.isoformat()})
    return _pedir("GET", f"/facturas?{consulta}", token=token)["facturas"]


# ---------- API del grupo UD1 (Django REST) ----------


def _desde_ud1(desde, hasta):
    """Traduce la API de UD1 al formato común.

    - Login: POST /auth/login/ con username y password; devuelve el JWT en "access".
    - Ventas: GET /ventas/. Solo cuentan las "activa"; las "anulada" devolvieron el stock.
      El tercero sale de GET /clientes/ (documento, nombres y apellidos).
    - Compras: cada lote de GET /lotes/ es una factura de compra: total = cantidad ×
      costo_unitario. El tercero sale de GET /proveedores/ (no guardan NIT).
    - Su API no filtra por fechas: el filtro se hace aquí.
    """
    token = _token_ud1()
    clientes = {c["id_cliente"]: c for c in _lista("/clientes/", token)}
    proveedores = {p["id_proveedor"]: p for p in _lista("/proveedores/", token)}

    facturas = []
    for venta in _lista("/ventas/", token):
        fecha = _fecha(venta["fecha"])
        if venta.get("estado") != "activa" or not desde <= fecha.date() <= hasta:
            continue
        cliente = clientes.get(venta["id_cliente"], {})
        nombre = f"{cliente.get('nombres', '')} {cliente.get('apellidos', '')}".strip()
        facturas.append(_factura(
            "venta", f"V-{venta['id_venta']:06d}", fecha,
            cliente.get("documento") or "", nombre or f"Cliente {venta['id_cliente']}",
            Decimal(str(venta["total"])),
        ))
    for lote in _lista("/lotes/", token):
        fecha = _fecha(lote["fecha_compra"])
        if not desde <= fecha.date() <= hasta:
            continue
        proveedor = proveedores.get(lote["id_proveedor"], {})
        total = Decimal(lote["cantidad"]) * Decimal(str(lote["costo_unitario"]))
        facturas.append(_factura(
            "compra", f"L-{lote['id_lote']:06d}", fecha,
            "", proveedor.get("nombre") or f"Proveedor {lote['id_proveedor']}", total,
        ))
    return facturas


def _token_ud1():
    """JWT de UD1, guardado TOKEN_SEGUNDOS para la misma URL y el mismo usuario."""
    config = current_app.config
    clave = (config["SEDE_REMOTA_URL"], config["SEDE_REMOTA_USUARIO"], config["SEDE_REMOTA_CLAVE"])
    guardado = _tokens.get(clave)
    if guardado and guardado[1] > reloj.monotonic():
        return guardado[0]
    token = _pedir("POST", "/auth/login/", {
        "username": config["SEDE_REMOTA_USUARIO"], "password": config["SEDE_REMOTA_CLAVE"],
    })["access"]
    _tokens[clave] = (token, reloj.monotonic() + TOKEN_SEGUNDOS)
    return token


def olvidar_tokens():
    """Borra los tokens guardados (por ejemplo, si la otra sede los rechaza)."""
    _tokens.clear()


def _factura(tipo, numero, fecha, documento, nombre, total):
    subtotal, iva = separar_iva(total)
    return {
        "tipo": tipo,
        "numero": numero,
        "fecha": fecha_iso(fecha),
        "tercero": {"documento": documento, "nombre": nombre},
        "subtotal": _texto(subtotal),
        "iva": _texto(iva),
        "total": _texto(total),
    }


def _fecha(texto):
    """Fecha y hora de Colombia a partir de "2026-10-30T10:15:00-05:00", "...Z" o "2026-10-30"."""
    if len(texto) == 10:
        return datetime.combine(date.fromisoformat(texto), time(), HORA_COLOMBIA)
    fecha = datetime.fromisoformat(texto)
    if fecha.tzinfo is None:
        return fecha.replace(tzinfo=HORA_COLOMBIA)
    return fecha.astimezone(HORA_COLOMBIA)


def _lista(ruta, token):
    """Lista completa de un recurso de Django REST, con o sin paginación."""
    datos = _pedir("GET", ruta, token=token)
    if isinstance(datos, list):
        return datos
    elementos = list(datos["results"])
    while datos.get("next"):
        siguiente = parse.urlsplit(datos["next"])
        # Detrás de ngrok, Django puede armar el enlace con http o con otro host: se usa
        # solo la ruta, sobre la misma URL base.
        base = parse.urlsplit(current_app.config["SEDE_REMOTA_URL"]).path.rstrip("/")
        ruta = siguiente.path.removeprefix(base) + (f"?{siguiente.query}" if siguiente.query else "")
        datos = _pedir("GET", ruta, token=token)
        elementos += datos["results"]
    return elementos


# ---------- HTTP ----------


def _pedir(metodo, ruta, cuerpo=None, token=None):
    """Hace la petición a la otra sede y devuelve el JSON. ruta es relativa a SEDE_REMOTA_URL."""
    base = current_app.config["SEDE_REMOTA_URL"].rstrip("/")
    url = base + ruta
    encabezados = {
        "Accept": "application/json",
        "User-Agent": "RepuAuto-consolidado",
        # Sin esto, ngrok gratis responde con su página de advertencia en lugar del JSON.
        "ngrok-skip-browser-warning": "true",
    }
    datos = None
    if cuerpo is not None:
        datos = json.dumps(cuerpo).encode()
        encabezados["Content-Type"] = "application/json"
    if token:
        encabezados["Authorization"] = f"Bearer {token}"
    peticion = request.Request(url, data=datos, headers=encabezados, method=metodo)
    try:
        with request.urlopen(peticion, timeout=ESPERA_SEGUNDOS) as respuesta:
            return json.loads(respuesta.read().decode())
    except url_error.HTTPError as http:
        if http.code in (401, 403):
            olvidar_tokens()
            raise SedeNoDisponible("La otra sede rechazó el usuario o la clave (SEDE_REMOTA_USUARIO y SEDE_REMOTA_CLAVE).")
        if http.code == 400 and "ngrok" in base:
            raise SedeNoDisponible(
                "La otra sede rechazó la dirección de ngrok. En su .env deben agregar .ngrok-free.app "
                "a DJANGO_ALLOWED_HOSTS y reiniciar su servidor."
            )
        if http.code == 429:
            raise SedeNoDisponible("La otra sede bloqueó los intentos por un momento (demasiados inicios de sesión). Espera un minuto.")
        if http.code == 404 and "ngrok" in base:
            raise SedeNoDisponible(f"El túnel de ngrok no responde en {base}. Revisa que la dirección sea la actual: cambia cada vez que reinician ngrok.")
        raise SedeNoDisponible(f"La otra sede respondió con error {http.code} en {ruta}.")
    except (url_error.URLError, TimeoutError, OSError):
        raise SedeNoDisponible(f"No hay conexión con la otra sede en {base}. ¿Está encendido su servidor?")
    except json.JSONDecodeError:
        raise SedeNoDisponible(
            f"La otra sede no respondió JSON en {ruta}. Si usan ngrok, revisa que la dirección termine en /api."
        )
