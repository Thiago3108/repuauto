"""Genera la imagen del modelo de base de datos de RepuAuto a partir de repuauto_bd.dbml.

    repuauto_bd.svg   el modelo relacional: tablas, columnas, llaves y relaciones

Uso, desde la raíz del proyecto:

    python docs/diagramas/generar_bd.py

La imagen repuauto_bd.png se saca del .svg (ver generar_casos_de_uso.py).

Las tablas, columnas, tipos y relaciones se leen del .dbml: si el modelo cambia, se
cambia allá y se vuelve a generar. Aquí solo se decide dónde va cada tabla (POSICION) y
por dónde pasa cada línea (RUTAS). Una tabla o relación nueva sin posición o sin ruta
detiene el programa con un mensaje que dice cuál falta.
"""
import re
from pathlib import Path

CARPETA = Path(__file__).parent
ANCHO_TABLA, ALTO_TITULO, ALTO_FILA = 262, 30, 22

# Esquina superior izquierda de cada tabla.
POSICION = {
    "estado_venta": (40, 120), "cliente": (350, 120), "usuario": (660, 120), "rol": (970, 120),
    "proveedor": (1290, 120),
    "venta": (350, 410), "compra": (970, 410),
    "detalle_venta": (350, 690), "repuesto": (660, 640), "detalle_compra": (970, 720),
    "repuesto_vehiculo": (1290, 600), "vehiculo": (1290, 760), "marca_vehiculo": (1290, 980),
    "categoria": (520, 990), "marca_repuesto": (810, 990),
}

# Color del título según el grupo (TableGroup) del .dbml.
COLORES = {
    "cuentas": "#2F5D8A", "clientes": "#3F7F6B", "vehiculos": "#7A5C99",
    "repuestos": "#B7791F", "ventas": "#B4533C", "compras": "#4A6FA5",
}
NOMBRES_DE_GRUPO = {
    "cuentas": "Cuentas (US-01)", "clientes": "Clientes (US-02)", "vehiculos": "Vehículos (US-03)",
    "repuestos": "Repuestos (US-04 y US-05)", "ventas": "Ventas (US-06 a US-08)", "compras": "Compras (US-09)",
}

# Recorrido de cada relación, de la tabla que tiene la llave foránea a la tabla referida.
# Cada punto es (tabla, lado, posición): lado es "arriba", "abajo", "izq" o "der", y posición
# es la distancia en píxeles desde la esquina superior izquierda de la tabla sobre ese lado.
# Entre el primer punto y el último, la línea dobla en ángulo recto: "h" sale horizontal,
# "v" sale vertical y ("hv", x) sale horizontal, baja o sube en esa x y llega horizontal.
RUTAS = {
    ("usuario", "id_rol"): [("usuario", "der", 60), ("rol", "izq", 60), "h"],
    ("cliente", "id_usuario"): [("cliente", "der", 100), ("usuario", "izq", 100), "h"],
    ("venta", "id_cliente"): [("venta", "arriba", 90), ("cliente", "abajo", 90), "v"],
    ("venta", "id_estado_venta"): [("venta", "izq", 60), ("estado_venta", "abajo", 130), "h"],
    ("venta", "id_vendedor"): [("venta", "der", 60), ("usuario", "abajo", 60), "h"],
    ("compra", "id_usuario"): [("compra", "izq", 60), ("usuario", "abajo", 200), "h"],
    ("compra", "id_proveedor"): [("compra", "der", 60), ("proveedor", "abajo", 130), "h"],
    ("detalle_venta", "id_venta"): [("detalle_venta", "arriba", 130), ("venta", "abajo", 130), "v"],
    ("detalle_venta", "id_repuesto"): [("detalle_venta", "der", 80), ("repuesto", "izq", 130), "h"],
    ("detalle_compra", "id_compra"): [("detalle_compra", "arriba", 130), ("compra", "abajo", 130), "v"],
    ("detalle_compra", "id_repuesto"): [("detalle_compra", "izq", 80), ("repuesto", "der", 160), "h"],
    ("repuesto_vehiculo", "id_repuesto"): [("repuesto_vehiculo", "izq", 20), ("repuesto", "der", 40), ("hv", 1262)],
    ("repuesto_vehiculo", "id_vehiculo"): [("repuesto_vehiculo", "abajo", 130), ("vehiculo", "arriba", 130), "v"],
    ("vehiculo", "id_marca_vehiculo"): [("vehiculo", "abajo", 130), ("marca_vehiculo", "arriba", 130), "v"],
    ("repuesto", "id_categoria"): [("repuesto", "abajo", 40), ("categoria", "arriba", 180), "v"],
    ("repuesto", "id_marca_repuesto"): [("repuesto", "abajo", 215), ("marca_repuesto", "arriba", 65), "v"],
}


# ---------- Lectura del .dbml ----------

def leer_dbml(texto):
    """Devuelve (tablas, relaciones, grupos). tablas: {nombre: [columna, ...]} con cada
    columna como dict(nombre, tipo, pk, fk, unica, obligatoria). relaciones: lista de
    (tabla, columna, tabla_referida, uno_a_uno)."""
    tablas, relaciones, grupos = {}, [], {}
    for nombre, cuerpo in re.findall(r"^Table (\w+) \{\n(.*?)^\}", texto, flags=re.S | re.M):
        columnas, pk_compuesta = [], set()
        for bloque in re.findall(r"indexes \{(.*?)\}", cuerpo, flags=re.S):
            for campos in re.findall(r"\(([^)]*)\) \[pk\]", bloque):
                pk_compuesta |= {c.strip() for c in campos.split(",")}
        cuerpo = re.sub(r"^\s*(indexes|checks) \{.*?^\s*\}", "", cuerpo, flags=re.S | re.M)
        for linea in cuerpo.splitlines():
            m = re.match(r"\s+(\w+) ([\w(),]+)(?: \[(.*)\])?\s*$", linea)
            if not m or m.group(1) == "Note":
                continue
            columna, tipo, opciones = m.group(1), m.group(2), m.group(3) or ""
            ref = re.search(r"ref: ([>-]) (\w+)\.\w+", opciones)
            if ref:
                relaciones.append((nombre, columna, ref.group(2), ref.group(1) == "-"))
            columnas.append({
                "nombre": columna, "tipo": tipo,
                "pk": bool(re.search(r"\bpk\b", opciones)) or columna in pk_compuesta,
                "fk": bool(ref),
                "unica": "unique" in opciones,
                "obligatoria": "not null" in opciones or bool(re.search(r"\bpk\b", opciones)) or columna in pk_compuesta,
            })
        tablas[nombre] = columnas
    for tabla, columna, referida in re.findall(r"^Ref: (\w+)\.(\w+) > (\w+)\.\w+", texto, flags=re.M):
        relaciones.append((tabla, columna, referida, False))
        next(c for c in tablas[tabla] if c["nombre"] == columna)["fk"] = True
    for grupo, cuerpo in re.findall(r"^TableGroup (\w+) \{\n(.*?)^\}", texto, flags=re.S | re.M):
        for tabla in cuerpo.split():
            grupos[tabla] = grupo
    return tablas, relaciones, grupos


# ---------- Dibujo ----------

def alto_de(columnas):
    return ALTO_TITULO + len(columnas) * ALTO_FILA + 8


def ancla(tablas, tabla, lado, posicion):
    x, y = POSICION[tabla]
    alto = alto_de(tablas[tabla])
    return {
        "arriba": (x + posicion, y), "abajo": (x + posicion, y + alto),
        "izq": (x, y + posicion), "der": (x + ANCHO_TABLA, y + posicion),
    }[lado]


def recorrido(inicio, fin, forma):
    (x0, y0), (x1, y1) = inicio, fin
    if forma == "h" and y0 != y1:      # sale horizontal y llega vertical
        return [(x0, y0), (x1, y0), (x1, y1)]
    if forma == "v" and x0 != x1:      # sale vertical y llega vertical: dobla a media altura
        medio = (y0 + y1) / 2
        return [(x0, y0), (x0, medio), (x1, medio), (x1, y1)]
    if isinstance(forma, tuple):       # ("hv", x): sale horizontal, dobla en esa x y llega horizontal
        return [(x0, y0), (forma[1], y0), (forma[1], y1), (x1, y1)]
    return [(x0, y0), (x1, y1)]


def etiqueta(punto, vecino, texto):
    """Cardinalidad junto al extremo de una línea, corrida hacia el lado del vecino."""
    (x, y), (vx, vy) = punto, vecino
    if abs(vx - x) > abs(vy - y):      # la línea sale horizontal
        return f'<text x="{x + (12 if vx > x else -12)}" y="{y - 6}" text-anchor="middle" class="card">{texto}</text>'
    return f'<text x="{x + 10}" y="{y + (16 if vy > y else -8)}" class="card">{texto}</text>'


def dibujar():
    tablas, relaciones, grupos = leer_dbml((CARPETA / "repuauto_bd.dbml").read_text(encoding="utf-8"))
    faltan = [t for t in tablas if t not in POSICION]
    faltan += [f"{t}.{c}" for t, c, _, _ in relaciones if (t, c) not in RUTAS]
    if faltan:
        raise SystemExit("Faltan en POSICION o en RUTAS de generar_bd.py: " + ", ".join(faltan))

    ancho = max(x for x, _ in POSICION.values()) + ANCHO_TABLA + 40
    alto = max(y + alto_de(tablas[t]) for t, (_, y) in POSICION.items()) + 110
    p = []
    add = p.append
    add(f'<rect width="{ancho}" height="{alto}" fill="#FFFFFF"/>')
    add(f'<text x="{ancho / 2}" y="46" text-anchor="middle" class="titulo">Modelo de base de datos - RepuAuto</text>')
    add(f'<text x="{ancho / 2}" y="74" text-anchor="middle" class="subtitulo">Modelo relacional en PostgreSQL: '
        f'{len(tablas)} tablas y {len(relaciones)} relaciones. Fuente: repuauto_bd.dbml</text>')

    for tabla, columna, referida, uno_a_uno in relaciones:
        inicio_def, fin_def, forma = RUTAS[(tabla, columna)]
        puntos = recorrido(ancla(tablas, *inicio_def), ancla(tablas, *fin_def), forma)
        add('<polyline points="' + " ".join(f"{x:.0f},{y:.0f}" for x, y in puntos) + '" class="relacion"/>')
        add(etiqueta(puntos[0], puntos[1], "0..1" if uno_a_uno else "N"))
        add(etiqueta(puntos[-1], puntos[-2], "1"))

    for tabla, columnas in tablas.items():
        x, y = POSICION[tabla]
        alto_tabla = alto_de(columnas)
        color = COLORES[grupos[tabla]]
        add(f'<rect x="{x}" y="{y}" width="{ANCHO_TABLA}" height="{alto_tabla}" rx="7" class="tabla"/>')
        add(f'<path d="M{x},{y + ALTO_TITULO} v-{ALTO_TITULO - 7} a7,7 0 0 1 7,-7 h{ANCHO_TABLA - 14} a7,7 0 0 1 7,7 v{ALTO_TITULO - 7} z" fill="{color}"/>')
        add(f'<text x="{x + ANCHO_TABLA / 2}" y="{y + 20}" text-anchor="middle" class="tabla-titulo">{tabla}</text>')
        for i, c in enumerate(columnas):
            yc = y + ALTO_TITULO + 17 + i * ALTO_FILA
            marca = "PK" if c["pk"] else ("FK" if c["fk"] else "")
            if c["pk"] and c["fk"]:
                marca = "PK FK"
            if marca:
                add(f'<text x="{x + 8}" y="{yc}" class="marca {"pk" if c["pk"] else "fk"}">{marca}</text>')
            nombre = c["nombre"] + ("" if c["obligatoria"] else " ?")
            desplazado = 46 if marca == "PK FK" else 32
            add(f'<text x="{x + desplazado}" y="{yc}" class="columna{" llave" if c["pk"] else ""}">{nombre}</text>')
            tipo = c["tipo"] + (" · U" if c["unica"] else "")
            add(f'<text x="{x + ANCHO_TABLA - 8}" y="{yc}" text-anchor="end" class="tipo">{tipo}</text>')

    # Convenciones
    ly = alto - 62
    add(f'<text x="40" y="{ly}" class="leyenda-titulo">Convenciones</text>')
    add(f'<text x="40" y="{ly + 22}" class="leyenda"><tspan class="pk">PK</tspan> llave primaria · '
        '<tspan class="fk">FK</tspan> llave foránea · U valor único · ? puede quedar vacío (NULL) · '
        'N y 1: muchas filas de una tabla apuntan a una fila de la otra · 0..1: a lo sumo una</text>')
    xg = 40
    for grupo, nombre in NOMBRES_DE_GRUPO.items():
        add(f'<rect x="{xg}" y="{ly + 34}" width="14" height="14" rx="3" fill="{COLORES[grupo]}"/>')
        add(f'<text x="{xg + 20}" y="{ly + 46}" class="leyenda">{nombre}</text>')
        xg += 34 + len(nombre) * 7.4

    cuerpo = "\n".join("  " + linea for linea in p)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" viewBox="0 0 {ancho} {alto}" font-family="Arial, Helvetica, sans-serif">
  <!-- RepuAuto - Modelo de base de datos. Lo genera generar_bd.py desde repuauto_bd.dbml: no se edita a mano. -->
  <defs>
    <style>
      .titulo {{ font-size: 24px; font-weight: bold; fill: #000; }}
      .subtitulo {{ font-size: 14px; fill: #44546A; }}
      .tabla {{ fill: #FFFFFF; stroke: #8FA3BA; stroke-width: 1.2; }}
      .tabla-titulo {{ font-size: 14px; font-weight: bold; fill: #FFFFFF; }}
      .columna {{ font-size: 12.5px; fill: #1F2D3D; }}
      .llave {{ font-weight: bold; }}
      .tipo {{ font-size: 11px; fill: #6B7785; }}
      .marca {{ font-size: 9.5px; font-weight: bold; }}
      .pk {{ fill: #B7791F; }}
      .fk {{ fill: #2F5D8A; }}
      .relacion {{ fill: none; stroke: #3C4A5C; stroke-width: 1.3; }}
      .card {{ font-size: 12px; font-weight: bold; fill: #3C4A5C; }}
      .leyenda-titulo {{ font-size: 14px; font-weight: bold; fill: #000; }}
      .leyenda {{ font-size: 12.5px; fill: #1F2D3D; }}
    </style>
  </defs>
{cuerpo}
</svg>
'''


if __name__ == "__main__":
    (CARPETA / "repuauto_bd.svg").write_text(dibujar(), encoding="utf-8")
    tablas, relaciones, _ = leer_dbml((CARPETA / "repuauto_bd.dbml").read_text(encoding="utf-8"))
    print(f"Listo: {len(tablas)} tablas y {len(relaciones)} relaciones.")
