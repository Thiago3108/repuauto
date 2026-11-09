"""Rutas de la API REST. Todas responden JSON, también los errores: {"error": "..."}.

POST /api/login       correo y clave -> token
GET  /api/facturas    ?desde=AAAA-MM-DD&hasta=AAAA-MM-DD&tipo=venta|compra (con token)
"""
from functools import wraps

from flask import g, jsonify, request
from werkzeug.exceptions import HTTPException

from app.api import bp, services
from app.auth import services as cuentas
from app.reportes.services import RangoInvalido, rango_de_fechas

ROLES_DE_LA_API = ("administrador",)


def error(mensaje, codigo):
    respuesta = jsonify({"error": mensaje})
    respuesta.status_code = codigo
    if codigo == 401:
        respuesta.headers["WWW-Authenticate"] = 'Bearer realm="repuauto"'
    return respuesta


def token_requerido(vista):
    """Exige el encabezado Authorization: Bearer <token> de un administrador activo.
    Deja al usuario en g.usuario."""

    @wraps(vista)
    def envoltura(*args, **kwargs):
        tipo, _, token = request.headers.get("Authorization", "").partition(" ")
        if tipo.lower() != "bearer" or not token.strip():
            return error("Falta el token. Envía el encabezado Authorization: Bearer <token>.", 401)
        try:
            usuario = services.usuario_del_token(token.strip())
        except services.TokenInvalido as invalido:
            return error(invalido.mensaje, 401)
        if not usuario.tiene_rol(*ROLES_DE_LA_API):
            return error("Solo un administrador puede usar la API.", 403)
        g.usuario = usuario
        return vista(*args, **kwargs)

    return envoltura


@bp.post("/login")
def login():
    """Recibe {"correo": "...", "clave": "..."} y devuelve un token de acceso."""
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return error('Envía un JSON con "correo" y "clave".', 400)
    correo, clave = datos.get("correo"), datos.get("clave")
    if not isinstance(correo, str) or not isinstance(clave, str) or not correo or not clave:
        return error('Envía un JSON con "correo" y "clave".', 400)

    usuario = cuentas.autenticar(correo, clave)
    if usuario is None:
        return error("Correo o contraseña incorrectos.", 401)
    if not usuario.tiene_rol(*ROLES_DE_LA_API):
        return error("Solo un administrador puede usar la API.", 403)
    return jsonify({
        "token": services.crear_token(usuario),
        "tipo": "Bearer",
        "expira_en": services.duracion_token(),
        "usuario": {"nombre": usuario.nombre, "rol": usuario.rol.nombre},
    })


@bp.get("/facturas")
@token_requerido
def facturas():
    """Facturas de venta y compra de esta sede en el rango. Sin fechas, el mes actual."""
    tipo = request.args.get("tipo", "").strip().lower() or None
    if tipo is not None and tipo not in services.TIPOS:
        return error('El tipo debe ser "venta" o "compra", o no enviarlo para traer las dos.', 400)
    try:
        desde, hasta = rango_de_fechas(
            request.args.get("desde", "").strip(), request.args.get("hasta", "").strip()
        )
    except RangoInvalido as rango:
        return error(rango.mensaje, 400)
    return jsonify(services.facturas(desde, hasta, tipo))


@bp.app_errorhandler(HTTPException)
def error_http(excepcion):
    """Bajo /api los errores HTTP (404, 405...) también responden JSON. En el resto de la
    app se dejan como estaban."""
    if not request.path.startswith(bp.url_prefix + "/"):
        return excepcion
    return error(excepcion.description, excepcion.code)
