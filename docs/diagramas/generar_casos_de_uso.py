"""Genera el diagrama de casos de uso de RepuAuto (versión 4).

Los casos de uso, los actores y las relaciones se definen una sola vez aquí, y de ahí
salen los dos archivos, para que nunca se contradigan:

    casos_de_uso.svg   el dibujo
    casos_de_uso.puml  la misma información en PlantUML

Uso, desde la raíz del proyecto:

    python docs/diagramas/generar_casos_de_uso.py

La imagen casos_de_uso.png se saca del .svg, por ejemplo con Chrome:

    google-chrome --headless --force-device-scale-factor=1.5 --window-size=2280,2282 \\
        --screenshot=docs/diagramas/casos_de_uso.png docs/diagramas/casos_de_uso.svg

Cada caso de uso corresponde a algo que la app hace hoy (ver los routes.py y services.py
de cada módulo). Si se agrega una función, se agrega aquí su caso de uso.
"""
from math import sqrt
from pathlib import Path

CARPETA = Path(__file__).parent

# ---------- Medidas ----------

ANCHO = 2280
RX, RY = 124, 26          # radios de cada caso de uso
FILA = 68                 # alto de una fila de casos de uso
ENCABEZADO = 40           # alto del título de cada módulo
MARGEN_MODULO = 16
# Centros de las columnas. En cada lado, "p" es la columna de los casos que inicia un
# actor (pegada a ese actor) y "s" la de los incluidos o extensiones.
COLUMNAS = {
    "I": {"p": 600, "s": 980, "x": 462, "ancho": 656},
    "D": {"p": 1700, "s": 1320, "x": 1182, "ancho": 656},
    "T": {"a": 600, "b": 980, "c": 1320, "d": 1700, "x": 462, "ancho": 1376},
}
SISTEMA_X, SISTEMA_ANCHO, SISTEMA_Y = 440, 1420, 100
X_ACTOR_IZQ, X_ACTOR_DER = 300, 2010

# ---------- Contenido ----------
# Módulo: (clave, título, lado, filas, casos). Caso: (id, columna, fila, nombre, código).
# El nombre usa "/" para partirse en dos líneas. Los casos sin código son pasos que el
# sistema hace dentro de otro caso de uso («include») o variantes opcionales («extend»).

MODULOS = [
    ("compras_cliente", "Mis compras", "I", 2, [
        ("c1", "p", 0, "Consultar historial/de compras", "US-08"),
        ("c2", "p", 1, "Ver detalle y estado/de una compra", "US-08"),
        ("c3", "s", 0, "Filtrar por estado", ""),
    ]),
    ("acceso", "Cuentas y acceso", "I", 3, [
        ("a1", "p", 0, "Registrarse", "US-01"),
        ("a2", "p", 1, "Iniciar sesión", "US-01"),
        ("a3", "p", 2, "Cerrar sesión", "US-01"),
        ("a4", "s", 0, "Validar datos y/contraseña segura", ""),
        ("a5", "s", 1, "Validar credenciales/y cuenta activa", ""),
    ]),
    ("catalogo", "Catálogo", "I", 3, [
        ("b1", "p", 1, "Consultar catálogo/de repuestos", "US-05"),
        ("b2", "s", 0, "Buscar por nombre/o código", ""),
        ("b3", "s", 1, "Filtrar por categoría", ""),
        ("b4", "s", 2, "Filtrar por vehículo/(marca, línea y año)", ""),
    ]),
    ("clientes", "Clientes", "I", 5, [
        ("d1", "p", 0, "Registrar cliente", "US-02"),
        ("d2", "p", 1, "Buscar y consultar/cliente", "US-02"),
        ("d3", "p", 2, "Actualizar cliente", "US-02"),
        ("d4", "p", 3, "Enlazar cuenta/del cliente", "US-02"),
        ("d5", "p", 4, "Quitar enlace/de la cuenta", "US-02"),
        ("d6", "s", 1, "Validar cédula/no repetida", ""),
        ("d7", "s", 3, "Verificar la cédula/del cliente", ""),
    ]),
    ("ventas", "Ventas", "I", 5, [
        ("e1", "p", 0, "Registrar venta", "US-06"),
        ("e2", "p", 2, "Consultar ventas/y su detalle", "US-06"),
        ("e3", "p", 3, "Completar venta/pendiente", "US-06"),
        ("e4", "p", 4, "Cancelar venta", "US-06"),
        ("e5", "s", 0, "Buscar cliente/por cédula", ""),
        ("e6", "s", 1, "Verificar y/descontar stock", ""),
        ("e7", "s", 2, "Filtrar por estado", ""),
        ("e8", "s", 4, "Devolver el stock", ""),
    ]),
    ("stock", "Stock", "I", 1, [
        ("f1", "p", 0, "Consultar stock/y alertas", "US-04"),
        ("f2", "s", 0, "Buscar repuesto", ""),
    ]),
    ("repuestos", "Repuestos e inventario", "D", 4, [
        ("g1", "p", 0, "Registrar repuesto", "US-04"),
        ("g2", "p", 1, "Editar repuesto", "US-04"),
        ("g3", "p", 2, "Desactivar repuesto", "US-04"),
        ("g4", "p", 3, "Ajustar stock", "US-04"),
        ("g5", "s", 0.5, "Validar código/no repetido", ""),
        ("g6", "s", 3, "Validar que el stock/no quede negativo", ""),
    ]),
    ("vehiculos", "Vehículos y compatibilidades", "D", 5, [
        ("h1", "p", 0, "Registrar vehículo", "US-03"),
        ("h2", "p", 1, "Editar vehículo", "US-03"),
        ("h3", "p", 2, "Eliminar vehículo", "US-03"),
        ("h4", "p", 3, "Asociar repuesto/compatible", "US-03"),
        ("h5", "p", 4, "Quitar repuesto/compatible", "US-03"),
        ("h6", "s", 0.5, "Validar que no/esté repetido", ""),
        ("h7", "s", 2, "Borrar sus/compatibilidades", ""),
        ("h8", "s", 3, "Validar que no esté/ya asociado", ""),
    ]),
    ("compras", "Proveedores y compras", "D", 4, [
        ("i1", "p", 0, "Registrar proveedor", "US-09"),
        ("i2", "p", 1, "Editar proveedor", "US-09"),
        ("i3", "p", 2, "Registrar compra", "US-09"),
        ("i4", "p", 3, "Consultar compras/y su detalle", "US-09"),
        ("i5", "s", 0.5, "Validar NIT/no repetido", ""),
        ("i6", "s", 2, "Sumar las cantidades/al stock", ""),
    ]),
    ("vendedores", "Cuentas de vendedor", "D", 2, [
        ("j1", "p", 0, "Crear cuenta/de vendedor", "US-01"),
        ("j2", "p", 1, "Activar o desactivar/cuenta de vendedor", "US-01"),
        ("j3", "s", 0, "Validar correo/no repetido", ""),
    ]),
    ("reportes", "Reportes", "D", 3, [
        ("k1", "p", 1, "Generar reportes/por rango de fechas", "US-07"),
        ("k2", "s", 0, "Informe consolidado", ""),
        ("k3", "s", 1, "Informe tabular", ""),
        ("k4", "s", 2, "Informe gráfico", ""),
    ]),
    ("integracion", "Integración entre sedes (API REST)", "T", 3, [
        ("l1", "a", 0, "Obtener token/de la API", "API"),
        ("l2", "a", 1, "Consultar facturas/en JSON", "API"),
        ("l3", "a", 2, "Consultar inventario/en JSON", "API"),
        ("l4", "b", 1.5, "Validar token", ""),
        ("l5", "d", 0, "Consultar consolidado/de facturas", "Integración"),
        ("l6", "d", 1, "Consultar inventario/de las sedes", "Integración"),
        ("l7", "c", 0.5, "Consultar la API/de la otra sede", ""),
    ]),
]

# (origen, destino, tipo). «include»: del caso base al incluido. «extend»: de la extensión a la base.
RELACIONES = [
    ("c3", "c1", "extend"),
    ("a1", "a4", "include"), ("a2", "a5", "include"),
    ("b2", "b1", "extend"), ("b3", "b1", "extend"), ("b4", "b1", "extend"),
    ("d1", "d6", "include"), ("d3", "d6", "include"), ("d4", "d7", "include"),
    ("e1", "e5", "include"), ("e1", "e6", "include"), ("e7", "e2", "extend"), ("e4", "e8", "include"),
    ("f2", "f1", "extend"),
    ("g1", "g5", "include"), ("g2", "g5", "include"), ("g4", "g6", "include"),
    ("h1", "h6", "include"), ("h2", "h6", "include"), ("h3", "h7", "include"), ("h4", "h8", "include"),
    ("i1", "i5", "include"), ("i2", "i5", "include"), ("i3", "i6", "include"),
    ("j1", "j3", "include"),
    ("k2", "k1", "extend"), ("k3", "k1", "extend"), ("k4", "k1", "extend"),
    ("l2", "l4", "include"), ("l3", "l4", "include"),
    ("l5", "l7", "include"), ("l6", "l7", "include"),
]

# Actor: (clave, nombre, nota bajo el nombre, lado, casos de uso en los que participa).
ACTORES = [
    ("cliente", "Cliente", "", "I", ["c1", "c2", "a1"]),
    ("usuario", "Usuario", "cualquier cuenta", "I", ["a2", "a3", "b1"]),
    ("vendedor", "Vendedor", "", "I", ["d1", "d2", "d3", "d4", "d5", "e1", "e2", "e3", "e4", "f1"]),
    ("pcstock", "Sistema PC Stock", "«sistema» · sede UD1", "I", ["l1", "l2", "l3"]),
    ("admin", "Administrador", "", "D", [
        "g1", "g2", "g3", "g4", "h1", "h2", "h3", "h4", "h5", "i1", "i2", "i3", "i4", "j1", "j2", "k1", "l5", "l6",
    ]),
]
HERENCIAS = [("cliente", "usuario"), ("vendedor", "usuario"), ("admin", "vendedor")]
# El sistema de la otra sede también responde cuando RepuAuto lo consulta (actor secundario).
SECUNDARIO = ("pcstock", "l7")


# ---------- Posiciones ----------

def calcular():
    """Devuelve (casos, marcos, alto): el centro de cada caso de uso, el marco de cada
    módulo y el alto total del dibujo."""
    casos, marcos = {}, []
    y = {"I": SISTEMA_Y + 44, "D": SISTEMA_Y + 44}
    for clave, titulo, lado, filas, lista in MODULOS:
        columnas = COLUMNAS[lado]
        if lado == "T":
            arriba = max(y.values())
            alto = ENCABEZADO + filas * FILA + 44   # espacio para la línea del actor secundario
        else:
            arriba = y[lado]
            alto = ENCABEZADO + filas * FILA + 8
            y[lado] = arriba + alto + MARGEN_MODULO
        marcos.append((titulo, columnas["x"], arriba, columnas["ancho"], alto))
        for ident, columna, fila, nombre, codigo in lista:
            cy = arriba + ENCABEZADO + FILA / 2 + fila * FILA
            casos[ident] = {"cx": columnas[columna], "cy": cy, "nombre": nombre, "codigo": codigo}
        fin = arriba + alto
    return casos, marcos, fin


def borde(caso, hacia_x, hacia_y, holgura=0):
    """Punto del borde de la elipse del caso de uso en dirección a (hacia_x, hacia_y)."""
    dx, dy = hacia_x - caso["cx"], hacia_y - caso["cy"]
    t = 1 / sqrt((dx / (RX + holgura)) ** 2 + (dy / (RY + holgura)) ** 2)
    return caso["cx"] + dx * t, caso["cy"] + dy * t


# ---------- SVG ----------

def dibujar():
    casos, marcos, fin = calcular()
    sistema_alto = fin + 24 - SISTEMA_Y
    alto = SISTEMA_Y + sistema_alto + 150
    p = []
    add = p.append

    add(f'<rect width="{ANCHO}" height="{alto}" fill="#FFFFFF"/>')
    add(f'<text x="{ANCHO / 2}" y="42" text-anchor="middle" class="titulo">Diagrama de casos de uso - RepuAuto</text>')
    add(f'<rect x="{SISTEMA_X}" y="{SISTEMA_Y}" width="{SISTEMA_ANCHO}" height="{sistema_alto}" rx="6" class="sistema"/>')
    add(f'<text x="{SISTEMA_X + SISTEMA_ANCHO / 2}" y="{SISTEMA_Y + 28}" text-anchor="middle" class="nombre">Sistema RepuAuto</text>')

    for titulo, x, y, ancho, alto_marco in marcos:
        add(f'<rect x="{x}" y="{y}" width="{ancho}" height="{alto_marco}" rx="10" class="modulo"/>')
        add(f'<text x="{x + 16}" y="{y + 26}" class="modulo-titulo">{titulo}</text>')

    # Posición de cada actor: a la altura media de sus casos de uso.
    actores = {}
    for clave, nombre, nota, lado, lista in ACTORES:
        cy = sum(casos[c]["cy"] for c in lista) / len(lista)
        actores[clave] = {"cx": X_ACTOR_IZQ if lado == "I" else X_ACTOR_DER, "cy": cy, "lado": lado}

    # Asociaciones actor - caso de uso
    for clave, _, _, lado, lista in ACTORES:
        a = actores[clave]
        x0 = a["cx"] + (26 if lado == "I" else -26)
        for ident in lista:
            # Llega al costado del caso de uso: así la línea queda en el pasillo entre el
            # actor y los casos, y no pasa por encima de otros.
            x1, y1 = casos[ident]["cx"] + (-RX if lado == "I" else RX), casos[ident]["cy"]
            add(f'<line x1="{x0}" y1="{a["cy"] - 8:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" class="asoc"/>')

    # Actor secundario: la línea pasa por debajo de los casos de uso de la API.
    a, destino = actores[SECUNDARIO[0]], casos[SECUNDARIO[1]]
    y_bajo = casos["l3"]["cy"] + RY + 22
    add(f'<polyline points="{a["cx"] + 26},{a["cy"] + 8:.1f} {SISTEMA_X + 14},{y_bajo:.1f} '
        f'{destino["cx"]},{y_bajo:.1f} {destino["cx"]},{destino["cy"] + RY:.1f}" class="asoc"/>')

    # Relaciones «include» y «extend»
    for origen, fin_rel, tipo in RELACIONES:
        o, d = casos[origen], casos[fin_rel]
        x0, y0 = borde(o, d["cx"], d["cy"])
        x1, y1 = borde(d, o["cx"], o["cy"], holgura=4)
        add(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" class="punteada"/>')
        # La etiqueta va cerca del origen cuando la línea es inclinada, para no chocar con otra.
        peso = 0.5 if abs(o["cy"] - d["cy"]) < 1 else 0.3
        ex, ey = x0 + (x1 - x0) * peso, y0 + (y1 - y0) * peso
        add(f'<text x="{ex:.1f}" y="{ey - 6:.1f}" text-anchor="middle" class="estereotipo">«{tipo}»</text>')

    # Casos de uso
    for caso in casos.values():
        lineas = caso["nombre"].split("/")
        total = len(lineas) + (1 if caso["codigo"] else 0)
        y0 = caso["cy"] - (total - 1) * 7.5 + 4.5
        add(f'<ellipse cx="{caso["cx"]}" cy="{caso["cy"]:.1f}" rx="{RX}" ry="{RY}" class="caso"/>')
        for i, linea in enumerate(lineas):
            add(f'<text x="{caso["cx"]}" y="{y0 + i * 15:.1f}" text-anchor="middle" class="texto">{linea}</text>')
        if caso["codigo"]:
            add(f'<text x="{caso["cx"]}" y="{y0 + len(lineas) * 15 - 1:.1f}" text-anchor="middle" class="codigo">{caso["codigo"]}</text>')

    # Actores
    for clave, nombre, nota, lado, _ in ACTORES:
        cx, cy = actores[clave]["cx"], actores[clave]["cy"]
        add(f'<g class="actor"><circle cx="{cx}" cy="{cy - 34:.1f}" r="13"/>'
            f'<line x1="{cx}" y1="{cy - 21:.1f}" x2="{cx}" y2="{cy + 10:.1f}"/>'
            f'<line x1="{cx - 20}" y1="{cy - 10:.1f}" x2="{cx + 20}" y2="{cy - 10:.1f}"/>'
            f'<line x1="{cx}" y1="{cy + 10:.1f}" x2="{cx - 16}" y2="{cy + 36:.1f}"/>'
            f'<line x1="{cx}" y1="{cy + 10:.1f}" x2="{cx + 16}" y2="{cy + 36:.1f}"/></g>')
        estilo = ' font-style="italic"' if clave == "usuario" else ""
        add(f'<text x="{cx}" y="{cy + 57:.1f}" text-anchor="middle" class="nombre"{estilo}>{nombre}</text>')
        if nota:
            add(f'<text x="{cx}" y="{cy + 73:.1f}" text-anchor="middle" class="codigo">{nota}</text>')

    # Herencia entre actores
    cliente, usuario, vendedor, admin = (actores[c] for c in ("cliente", "usuario", "vendedor", "admin"))
    x = X_ACTOR_IZQ
    add(f'<line x1="{x}" y1="{cliente["cy"] + 66:.1f}" x2="{x}" y2="{usuario["cy"] - 52:.1f}" class="asoc" marker-end="url(#triangulo)"/>')
    add(f'<line x1="{x}" y1="{vendedor["cy"] - 52:.1f}" x2="{x}" y2="{usuario["cy"] + 82:.1f}" class="asoc" marker-end="url(#triangulo)"/>')
    # El administrador está al otro lado: la línea rodea el sistema por arriba.
    add(f'<polyline points="{admin["cx"]},{admin["cy"] - 52:.1f} {admin["cx"]},72 70,72 70,{vendedor["cy"] - 10:.1f} '
        f'{x - 26},{vendedor["cy"] - 10:.1f}" class="asoc" marker-end="url(#triangulo)"/>')

    # Nota del administrador
    nx, ny = admin["cx"] + 4, admin["cy"] + 96
    add(f'<path d="M {nx} {ny} L {nx + 188} {ny} L {nx + 200} {ny + 12} L {nx + 200} {ny + 66} L {nx} {ny + 66} Z" class="nota"/>')
    add(f'<line x1="{admin["cx"] + 30}" y1="{ny - 30}" x2="{admin["cx"] + 30}" y2="{ny}" class="nota-linea"/>')
    for i, linea in enumerate(("Hereda del vendedor: también", "atiende clientes, registra", "ventas y consulta el stock.")):
        add(f'<text x="{nx + 10}" y="{ny + 20 + i * 17}" class="nota-texto">{linea}</text>')

    # Convenciones
    ly = SISTEMA_Y + sistema_alto + 40
    lx = SISTEMA_X
    add(f'<text x="{lx}" y="{ly}" class="nombre">Convenciones</text>')
    convenciones = [
        ("asoc", "", "El actor participa en el caso de uso."),
        ("punteada", "«include»", "El caso de uso siempre ejecuta el otro (la flecha apunta al incluido)."),
        ("punteada", "«extend»", "Variante opcional del caso de uso (la flecha apunta al caso que extiende)."),
        ("herencia", "", "Un actor hereda los casos de uso de otro (la flecha apunta al actor general)."),
    ]
    for i, (clase, etiqueta, texto) in enumerate(convenciones):
        x0, y0 = lx + (i % 2) * 720, ly + 28 + (i // 2) * 30
        marcador = ' marker-end="url(#triangulo)"' if clase == "herencia" else ""
        add(f'<line x1="{x0}" y1="{y0}" x2="{x0 + 70}" y2="{y0}" class="{"asoc" if clase == "herencia" else clase}"{marcador}/>')
        if etiqueta:
            add(f'<text x="{x0 + 35}" y="{y0 - 6}" text-anchor="middle" class="estereotipo">{etiqueta}</text>')
        add(f'<text x="{x0 + 90}" y="{y0 + 4}" class="leyenda">{texto}</text>')
    add(f'<text x="{lx}" y="{ly + 96}" class="pie">Los códigos US-xx son las historias de usuario del backlog. '
        'API e Integración: conexión con la sede del grupo UD1 (docs/API.md). '
        'Los casos sin código son pasos que el sistema ejecuta dentro de otro caso de uso.</text>')

    cuerpo = "\n".join("  " + linea for linea in p)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{ANCHO}" height="{alto}" viewBox="0 0 {ANCHO} {alto}" font-family="Arial, Helvetica, sans-serif">
  <!-- RepuAuto - Diagrama de casos de uso (versión 4). Lo genera generar_casos_de_uso.py: no se edita a mano. -->
  <defs>
    <marker id="flecha" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="9" markerHeight="9" orient="auto">
      <path d="M0,0 L10,5 L0,10" fill="none" stroke="#3C4A5C" stroke-width="1.5"/>
    </marker>
    <marker id="triangulo" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="14" markerHeight="14" orient="auto">
      <path d="M0,0 L12,6 L0,12 z" fill="#FFFFFF" stroke="#3C4A5C" stroke-width="1.2"/>
    </marker>
    <style>
      .titulo {{ font-size: 24px; font-weight: bold; fill: #000; }}
      .nombre {{ font-size: 15px; font-weight: bold; fill: #000; }}
      .texto {{ font-size: 13px; fill: #000; }}
      .codigo {{ font-size: 10.5px; fill: #44546A; }}
      .estereotipo {{ font-size: 12px; fill: #3C4A5C; }}
      .leyenda {{ font-size: 13px; fill: #1F2D3D; }}
      .pie {{ font-size: 12px; fill: #6B7785; }}
      .caso {{ fill: #F2F6FB; stroke: #2F5D8A; stroke-width: 1.2; }}
      .sistema {{ fill: none; stroke: #2F5D8A; stroke-width: 1.6; }}
      .modulo {{ fill: #FBFCFE; stroke: #B7C6DA; stroke-width: 1; stroke-dasharray: 5 4; }}
      .modulo-titulo {{ font-size: 13px; font-weight: bold; fill: #2F5D8A; }}
      .actor circle, .actor line {{ fill: #FFFFFF; stroke: #2F5D8A; stroke-width: 1.4; }}
      .asoc {{ stroke: #3C4A5C; stroke-width: 1.2; fill: none; }}
      .punteada {{ stroke: #3C4A5C; stroke-width: 1.2; stroke-dasharray: 7 5; fill: none; marker-end: url(#flecha); }}
      .nota {{ fill: #FFF8E1; stroke: #C9A227; stroke-width: 1.2; }}
      .nota-linea {{ stroke: #C9A227; stroke-width: 1.2; }}
      .nota-texto {{ font-size: 12.5px; fill: #000; }}
    </style>
  </defs>
{cuerpo}
</svg>
'''


# ---------- PlantUML ----------

def plantuml():
    lineas = [
        "@startuml casos_de_uso",
        "' RepuAuto - Diagrama de casos de uso (versión 4).",
        "' Lo genera generar_casos_de_uso.py junto con casos_de_uso.svg: no se edita a mano.",
        "",
        "left to right direction",
        "skinparam shadowing false",
        "skinparam defaultFontName Arial",
        "skinparam usecase {",
        "  BackgroundColor #F2F6FB",
        "  BorderColor #2F5D8A",
        "}",
        "skinparam actor {",
        "  BorderColor #2F5D8A",
        "  BackgroundColor #FFFFFF",
        "}",
        "",
        "title Diagrama de casos de uso - RepuAuto",
        "",
    ]
    for clave, nombre, nota, _, _ in ACTORES:
        etiqueta = f"//{nombre}//" if clave == "usuario" else nombre
        if clave == "pcstock":
            etiqueta = f"{nombre}\\n<<sistema>>"
        lineas.append(f'actor "{etiqueta}" as {clave}')
    lineas.append("")
    for hijo, padre in HERENCIAS:
        lineas.append(f"{padre} <|-- {hijo}")
    lineas += ["", 'rectangle "Sistema RepuAuto" {']
    for _, titulo, _, _, lista in MODULOS:
        lineas.append(f'  package "{titulo}" {{')
        for ident, _, _, nombre, codigo in lista:
            texto = nombre.replace("/", "\\n") + (f"\\n<size:10>{codigo}</size>" if codigo else "")
            lineas.append(f'    usecase "{texto}" as {ident}')
        lineas.append("  }")
    lineas += ["}", "", "' El actor participa en el caso de uso"]
    for clave, _, _, _, lista in ACTORES:
        lineas += [f"{clave} -- {ident}" for ident in lista]
    lineas += ["", "' El sistema de la otra sede responde cuando RepuAuto lo consulta (actor secundario)",
               f"{SECUNDARIO[1]} -- {SECUNDARIO[0]}", "", "' Relaciones entre casos de uso"]
    for origen, fin, tipo in RELACIONES:
        lineas.append(f"{origen} ..> {fin} : <<{tipo}>>")
    lineas += [
        "",
        "note right of admin",
        "  Hereda del vendedor: también atiende clientes,",
        "  registra ventas y consulta el stock.",
        "end note",
        "",
        "footer Los códigos US-xx son las historias de usuario del backlog. API e Integración: conexión con la sede del grupo UD1.",
        "@enduml",
        "",
    ]
    return "\n".join(lineas)


if __name__ == "__main__":
    (CARPETA / "casos_de_uso.svg").write_text(dibujar(), encoding="utf-8")
    (CARPETA / "casos_de_uso.puml").write_text(plantuml(), encoding="utf-8")
    casos = sum(len(lista) for *_, lista in MODULOS)
    print(f"Listo: {casos} casos de uso, {len(RELACIONES)} relaciones y {len(ACTORES)} actores.")
