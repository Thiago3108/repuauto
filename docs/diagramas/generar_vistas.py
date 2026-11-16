"""Genera el diagrama de vistas por usuario de RepuAuto (versión 3).

Las vistas se definen una sola vez aquí y de ahí salen los dos archivos:

    vistas_usuario.svg   el dibujo
    vistas_usuario.puml  la misma información en PlantUML (diagrama WBS)

Uso, desde la raíz del proyecto:

    python docs/diagramas/generar_vistas.py

La imagen vistas_usuario.png se saca del .svg (ver generar_casos_de_uso.py).

Los códigos UI-xx son los del plan de trabajo. Cada grupo dice quién ve esas vistas,
según la matriz de roles (app/menu.py y @rol_requerido en cada routes.py).
"""
from pathlib import Path

CARPETA = Path(__file__).parent

# Grupo: (quién las ve, vistas). Vista: (código, nombre, historia, dirección, pantallas).
GRUPOS = [
    ("Sin iniciar sesión", [
        ("UI-01", "Iniciar sesión", "US-01", "/auth/login", []),
        ("UI-02", "Registro de cliente", "US-01", "/auth/registro", []),
    ]),
    ("Todos los roles", [
        ("UI-03", "Inicio", "US-01", "/", ["Cifras del día según el rol", "Accesos a sus módulos"]),
        ("UI-04", "Catálogo", "US-05", "/catalogo/", [
            "Búsqueda por nombre o código", "Filtro por categoría", "Filtro por marca, línea y año",
        ]),
    ]),
    ("Cliente", [
        ("UI-05", "Mis compras", "US-08", "/ventas/mis-compras", [
            "Historial, con filtro por estado", "Detalle y estado de una compra",
        ]),
    ]),
    ("Vendedor y administrador", [
        ("UI-06", "Registro de venta", "US-06", "/ventas/nueva", []),
        ("UI-07", "Ventas registradas", "US-06", "/ventas/", [
            "Lista, con filtro por estado", "Detalle de la venta", "Completar o cancelar",
        ]),
        ("UI-08", "Clientes", "US-02", "/clientes/", [
            "Lista y búsqueda", "Detalle del cliente", "Registrar y editar", "Enlazar su cuenta",
        ]),
        ("UI-09", "Stock y alertas", "US-04", "/repuestos/stock", []),
    ]),
    ("Solo administrador", [
        ("UI-10", "Repuestos", "US-04", "/repuestos/", ["Lista y búsqueda", "Registrar y editar", "Ajustar stock"]),
        ("UI-11", "Vehículos", "US-03", "/vehiculos/", ["Lista, registro y edición", "Repuestos compatibles"]),
        ("UI-12", "Reportes", "US-07", "/reportes/", ["Informe consolidado", "Informe tabular", "Informe gráfico"]),
        ("UI-13", "Cuentas de vendedor", "US-01", "/auth/", []),
        ("UI-14", "Proveedores y compras", "US-09", "/compras/", [
            "Compras y su detalle", "Registrar compra", "Proveedores: lista y formulario",
        ]),
        ("UI-15", "Consolidado de sedes", "Integración", "/consolidado/", [
            "Facturas de las dos sedes", "Inventario de las dos sedes",
        ]),
    ]),
]

# Las vistas del administrador van en dos columnas para que el dibujo no quede tan alto.
COLUMNAS = [[0, 1, 2], [3], [4, "a"], [4, "b"]]
ANCHO_COL, SEPARACION, MARGEN = 330, 26, 40
ALTO_VISTA, ALTO_PANTALLA = 62, 22


def alto_de(vista):
    return ALTO_VISTA + len(vista[4]) * ALTO_PANTALLA + (10 if vista[4] else 0)


def dibujar():
    p = []
    add = p.append
    y_inicio = 150
    alto_total = 0
    for i, columna in enumerate(COLUMNAS):
        x = MARGEN + i * (ANCHO_COL + SEPARACION)
        y = y_inicio
        grupos = [g for g in columna if isinstance(g, int)]
        mitad = columna[-1] if isinstance(columna[-1], str) else None
        for g in grupos:
            titulo, vistas = GRUPOS[g]
            if mitad:
                corte = (len(vistas) + 1) // 2
                vistas = vistas[:corte] if mitad == "a" else vistas[corte:]
            alto_grupo = 46 + sum(alto_de(v) + 12 for v in vistas) + 4
            add(f'<rect x="{x}" y="{y}" width="{ANCHO_COL}" height="{alto_grupo}" rx="12" class="grupo"/>')
            if mitad != "b":
                add(f'<text x="{x + 16}" y="{y + 28}" class="grupo-titulo">{titulo}</text>')
            else:
                add(f'<text x="{x + 16}" y="{y + 28}" class="grupo-titulo">{titulo} (continuación)</text>')
            yv = y + 46
            for codigo, nombre, historia, direccion, pantallas in vistas:
                alto = alto_de((codigo, nombre, historia, direccion, pantallas))
                add(f'<rect x="{x + 12}" y="{yv}" width="{ANCHO_COL - 24}" height="{alto}" rx="9" class="vista"/>')
                add(f'<rect x="{x + 24}" y="{yv + 12}" width="50" height="22" rx="6" class="codigo-caja"/>')
                add(f'<text x="{x + 49}" y="{yv + 27}" text-anchor="middle" class="codigo">{codigo}</text>')
                add(f'<text x="{x + 84}" y="{yv + 28}" class="vista-titulo">{nombre}</text>')
                add(f'<text x="{x + 24}" y="{yv + 50}" class="detalle">{historia} · <tspan class="ruta">{direccion}</tspan></text>')
                for j, pantalla in enumerate(pantallas):
                    yp = yv + ALTO_VISTA + 8 + j * ALTO_PANTALLA
                    add(f'<circle cx="{x + 32}" cy="{yp - 4}" r="2.6" class="punto"/>')
                    add(f'<text x="{x + 44}" y="{yp}" class="pantalla">{pantalla}</text>')
                yv += alto + 12
            y += alto_grupo + 18
        alto_total = max(alto_total, y)

    ancho = MARGEN * 2 + len(COLUMNAS) * ANCHO_COL + (len(COLUMNAS) - 1) * SEPARACION
    alto = alto_total + 50
    cabecera = [
        f'<rect width="{ancho}" height="{alto}" fill="#FFFFFF"/>',
        f'<text x="{ancho / 2}" y="46" text-anchor="middle" class="titulo">Vistas por usuario - RepuAuto</text>',
        f'<text x="{ancho / 2}" y="74" text-anchor="middle" class="subtitulo">Qué pantallas ve cada rol. '
        'El administrador ve además todo lo del vendedor.</text>',
        f'<rect x="{MARGEN}" y="96" width="{ancho - MARGEN * 2}" height="36" rx="10" class="raiz"/>',
        f'<text x="{ancho / 2}" y="120" text-anchor="middle" class="raiz-texto">RepuAuto · 15 vistas</text>',
    ]
    pie = (f'<text x="{MARGEN}" y="{alto - 18}" class="pie">Los códigos UI-xx son los del plan de trabajo y las historias US-xx, '
           'las del backlog. Debajo de cada vista están las pantallas que la componen.</text>')
    cuerpo = "\n".join("  " + linea for linea in cabecera + p + [pie])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" viewBox="0 0 {ancho} {alto}" font-family="Arial, Helvetica, sans-serif">
  <!-- RepuAuto - Vistas por usuario (versión 3). Lo genera generar_vistas.py: no se edita a mano. -->
  <defs>
    <style>
      .titulo {{ font-size: 24px; font-weight: bold; fill: #000; }}
      .subtitulo {{ font-size: 14px; fill: #44546A; }}
      .raiz {{ fill: #2F5D8A; }}
      .raiz-texto {{ font-size: 15px; font-weight: bold; fill: #FFFFFF; }}
      .grupo {{ fill: #F6F9FC; stroke: #B7C6DA; stroke-width: 1.2; }}
      .grupo-titulo {{ font-size: 15px; font-weight: bold; fill: #2F5D8A; }}
      .vista {{ fill: #FFFFFF; stroke: #2F5D8A; stroke-width: 1.2; }}
      .vista-titulo {{ font-size: 15px; font-weight: bold; fill: #000; }}
      .codigo-caja {{ fill: #DCE6F2; }}
      .codigo {{ font-size: 12px; font-weight: bold; fill: #1F3D5C; }}
      .detalle {{ font-size: 12px; fill: #44546A; }}
      .ruta {{ font-family: "DejaVu Sans Mono", Consolas, monospace; font-size: 11.5px; }}
      .pantalla {{ font-size: 13px; fill: #1F2D3D; }}
      .punto {{ fill: #2F5D8A; }}
      .pie {{ font-size: 12px; fill: #6B7785; }}
    </style>
  </defs>
{cuerpo}
</svg>
'''


def plantuml():
    lineas = [
        "@startwbs vistas_usuario",
        "' RepuAuto - Vistas por usuario (versión 3).",
        "' Lo genera generar_vistas.py junto con vistas_usuario.svg: no se edita a mano.",
        "",
        "title Vistas por usuario - RepuAuto",
        "",
        "* RepuAuto",
    ]
    for titulo, vistas in GRUPOS:
        lineas.append(f"** {titulo}")
        for codigo, nombre, historia, _, pantallas in vistas:
            lineas.append(f"***:{codigo} {nombre}\n<size:10>{historia}</size>;")
            lineas += [f"**** {pantalla}" for pantalla in pantallas]
    lineas += ["@endwbs", ""]
    return "\n".join(lineas)


if __name__ == "__main__":
    (CARPETA / "vistas_usuario.svg").write_text(dibujar(), encoding="utf-8")
    (CARPETA / "vistas_usuario.puml").write_text(plantuml(), encoding="utf-8")
    print(f"Listo: {sum(len(v) for _, v in GRUPOS)} vistas en {len(GRUPOS)} grupos.")
