"""Genera el diagrama de actividades "Consultar el consolidado de sedes" (integración).

    actividades_consolidado.svg   el dibujo, con un carril por participante
    actividades_consolidado.puml  el mismo flujo en PlantUML

Uso, desde la raíz del proyecto:

    python docs/diagramas/generar_actividades_consolidado.py

La imagen actividades_consolidado.png se saca del .svg (ver generar_casos_de_uso.py).

El flujo es el de app/consolidado/services.py (informe) y app/consolidado/sedes.py
(facturas_remotas): si cambia allá, se cambia aquí en ACTIVIDADES, FLECHAS y PLANTUML.
"""
from pathlib import Path

CARPETA = Path(__file__).parent
ANCHO, ALTO = 1350, 1120
ARRIBA = 96                     # donde empiezan los carriles
# Carril: (título, x inicial, ancho)
CARRILES = [
    ("Administrador", 40, 330),
    ("RepuAuto · sede Bucaramanga", 370, 520),
    ("PC Stock · sede UD1", 890, 420),
]
A, R, P = 205, 630, 1100        # centro de cada carril

# Actividad: clave -> (centro x, centro y, ancho, líneas). Las decisiones llevan "?" en la clave.
ACTIVIDADES = {
    "abrir": (A, 200, 270, ["Abrir Consolidado de sedes", "y elegir fechas y filtros"]),
    "propias": (R, 200, 320, ["Leer las facturas de esta sede", "en la base de datos"]),
    "token?": (R, 310, 250, ["¿Hay un token vigente", "de la otra sede?"]),
    "pedir_token": (R, 430, 300, ["Pedir un token:", "POST /api/login con correo y clave"]),
    "dar_token": (P, 430, 320, ["Validar correo, clave y rol", "y entregar el token"]),
    "pedir_facturas": (R, 560, 320, ["Pedir las facturas del rango:", "GET /api/facturas con el token"]),
    "responder": (P, 560, 320, ["Validar el token y responder", "sus ventas y compras en JSON"]),
    "bien?": (R, 700, 250, ["¿La otra sede", "respondió bien?"]),
    "juntar": (R, 830, 330, ["Juntar las facturas de las dos sedes,", "aplicar los filtros y sumar por sede"]),
    "ver": (A, 830, 270, ["Ver los totales por sede,", "el consolidado y las facturas"]),
    "aviso": (R, 980, 330, ["Preparar el aviso con la causa", "y dejar solo las facturas de esta sede"]),
    "ver_aviso": (A, 980, 270, ["Ver el aviso y las facturas", "de Bucaramanga"]),
}
ALTO_ACTIVIDAD, ALTO_DECISION = 56, 78


def caja(clave):
    cx, cy, ancho, _ = ACTIVIDADES[clave]
    alto = ALTO_DECISION if clave.endswith("?") else ALTO_ACTIVIDAD
    return cx, cy, ancho / 2, alto / 2


def lado(clave, cual, corrimiento=0):
    cx, cy, mx, my = caja(clave)
    return {
        "arriba": (cx + corrimiento, cy - my), "abajo": (cx + corrimiento, cy + my),
        "izq": (cx - mx, cy + corrimiento), "der": (cx + mx, cy + corrimiento),
    }[cual]


# Flecha: (puntos, etiqueta, posición de la etiqueta). Los puntos intermedios van a mano.
def flechas():
    return [
        ([(A, 157), lado("abrir", "arriba")], "", None),
        ([lado("abrir", "der"), lado("propias", "izq")], "", None),
        ([lado("propias", "abajo"), lado("token?", "arriba")], "", None),
        ([lado("token?", "abajo"), lado("pedir_token", "arriba")], "no", (R + 14, 366)),
        ([lado("pedir_token", "der"), lado("dar_token", "izq")], "", None),
        ([lado("dar_token", "abajo"), (P, 495), (R + 90, 495), lado("pedir_facturas", "arriba", 90)],
         "token (se guarda 4 minutos)", (865, 487)),
        ([lado("token?", "izq"), (410, 310), (410, 560), lado("pedir_facturas", "izq")], "sí", (424, 302)),
        ([lado("pedir_facturas", "der"), lado("responder", "izq")], "", None),
        ([lado("responder", "abajo"), (P, 630), (R, 630), lado("bien?", "arriba")],
         "JSON, o un error si no responde", (865, 622)),
        ([lado("bien?", "abajo"), lado("juntar", "arriba")], "sí", (R + 14, 757)),
        ([lado("juntar", "izq"), lado("ver", "der")], "", None),
        ([lado("ver", "abajo"), (A, 905)], "", None),
        ([lado("bien?", "der"), (850, 700), (850, 980), lado("aviso", "der")], "no", (790, 692)),
        ([lado("aviso", "izq"), lado("ver_aviso", "der")], "", None),
        ([lado("ver_aviso", "abajo"), (A, 1055)], "", None),
    ]


NOTA = (912, 660, 376, [
    "Causas que el aviso distingue:",
    "• el servidor o el túnel de ngrok está apagado;",
    "• la otra sede rechazó el usuario o la clave;",
    "• respondió datos que no se entienden.",
    "La página nunca se cae: muestra lo que sí tiene.",
])


def dibujar():
    p = []
    add = p.append
    add(f'<rect width="{ANCHO}" height="{ALTO}" fill="#FFFFFF"/>')
    add(f'<text x="{ANCHO / 2}" y="44" text-anchor="middle" class="titulo">'
        'Diagrama de actividades: Consultar el consolidado de sedes (integración)</text>')
    add(f'<text x="{ANCHO / 2}" y="70" text-anchor="middle" class="subtitulo">'
        'Cómo RepuAuto junta sus facturas con las de la sede del grupo UD1 a través de la API REST</text>')

    for titulo, x, ancho in CARRILES:
        add(f'<rect x="{x}" y="{ARRIBA}" width="{ancho}" height="{ALTO - ARRIBA - 30}" class="carril"/>')
        add(f'<rect x="{x}" y="{ARRIBA}" width="{ancho}" height="34" class="carril-titulo-caja"/>')
        add(f'<text x="{x + ancho / 2}" y="{ARRIBA + 23}" text-anchor="middle" class="carril-titulo">{titulo}</text>')

    for puntos, etiqueta, posicion in flechas():
        add('<polyline points="' + " ".join(f"{x:.0f},{y:.0f}" for x, y in puntos) + '" class="flecha"/>')
        if etiqueta:
            ancla = "end" if posicion[0] > 800 else "start"
            add(f'<text x="{posicion[0]}" y="{posicion[1]}" text-anchor="{ancla}" class="etiqueta">{etiqueta}</text>')

    for clave, (cx, cy, ancho, lineas) in ACTIVIDADES.items():
        if clave.endswith("?"):
            mx, my = ancho / 2, ALTO_DECISION / 2
            add(f'<polygon points="{cx},{cy - my} {cx + mx},{cy} {cx},{cy + my} {cx - mx},{cy}" class="decision"/>')
        else:
            add(f'<rect x="{cx - ancho / 2}" y="{cy - ALTO_ACTIVIDAD / 2}" width="{ancho}" height="{ALTO_ACTIVIDAD}" rx="18" class="actividad"/>')
        y0 = cy - (len(lineas) - 1) * 9 + 5
        for i, linea in enumerate(lineas):
            add(f'<text x="{cx}" y="{y0 + i * 18}" text-anchor="middle" class="texto">{linea}</text>')

    # Inicio y finales
    add(f'<circle cx="{A}" cy="148" r="9" class="inicio"/>')
    for y in (916, 1066):
        add(f'<circle cx="{A}" cy="{y}" r="12" class="fin-borde"/><circle cx="{A}" cy="{y}" r="7" class="inicio"/>')

    # Nota
    x, y, ancho, lineas = NOTA
    alto = 22 + len(lineas) * 19
    add(f'<path d="M{x},{y} h{ancho - 14} l14,14 v{alto - 14} h-{ancho} z" class="nota"/>')
    add(f'<line x1="{x}" y1="{y + alto}" x2="{lado("aviso", "der")[0] - 6}" y2="{lado("aviso", "der")[1] - 20}" class="nota-linea"/>')
    for i, linea in enumerate(lineas):
        peso = ' font-weight="bold"' if i == 0 else ""
        add(f'<text x="{x + 12}" y="{y + 22 + i * 19}" class="nota-texto"{peso}>{linea}</text>')

    add(f'<text x="40" y="{ALTO - 10}" class="pie">El inventario de las dos sedes sigue el mismo flujo con GET /api/inventario. '
        'PC Stock consulta a RepuAuto igual, en el otro sentido.</text>')

    cuerpo = "\n".join("  " + linea for linea in p)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{ANCHO}" height="{ALTO}" viewBox="0 0 {ANCHO} {ALTO}" font-family="Arial, Helvetica, sans-serif">
  <!-- RepuAuto - Actividades del consolidado de sedes. Lo genera generar_actividades_consolidado.py. -->
  <defs>
    <marker id="punta" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#3C4A5C"/>
    </marker>
    <style>
      .titulo {{ font-size: 21px; font-weight: bold; fill: #000; }}
      .subtitulo {{ font-size: 13.5px; fill: #44546A; }}
      .carril {{ fill: #FFFFFF; stroke: #2F5D8A; stroke-width: 1.4; }}
      .carril-titulo-caja {{ fill: #DCE6F2; stroke: #2F5D8A; stroke-width: 1.4; }}
      .carril-titulo {{ font-size: 14.5px; font-weight: bold; fill: #1F3D5C; }}
      .actividad {{ fill: #F2F6FB; stroke: #2F5D8A; stroke-width: 1.3; }}
      .decision {{ fill: #FFFFFF; stroke: #2F5D8A; stroke-width: 1.3; }}
      .texto {{ font-size: 13px; fill: #000; }}
      .flecha {{ fill: none; stroke: #3C4A5C; stroke-width: 1.4; marker-end: url(#punta); }}
      .etiqueta {{ font-size: 12px; font-weight: bold; fill: #3C4A5C; }}
      .inicio {{ fill: #1F2D3D; }}
      .fin-borde {{ fill: #FFFFFF; stroke: #1F2D3D; stroke-width: 1.6; }}
      .nota {{ fill: #FFF8E1; stroke: #C9A227; stroke-width: 1.2; }}
      .nota-linea {{ stroke: #C9A227; stroke-width: 1.2; stroke-dasharray: 4 4; }}
      .nota-texto {{ font-size: 12.5px; fill: #000; }}
      .pie {{ font-size: 12px; fill: #6B7785; }}
    </style>
  </defs>
{cuerpo}
</svg>
'''


PLANTUML = """@startuml actividades_consolidado
' RepuAuto - Actividades: Consultar el consolidado de sedes (integración).
' Lo genera generar_actividades_consolidado.py junto con actividades_consolidado.svg.

title Diagrama de actividades: Consultar el consolidado de sedes (integración)

|Administrador|
start
:Abrir Consolidado de sedes
y elegir fechas y filtros;
|RepuAuto · sede Bucaramanga|
:Leer las facturas de esta sede
en la base de datos;
if (¿Hay un token vigente
de la otra sede?) then (no)
  :Pedir un token:
  POST /api/login con correo y clave;
  |PC Stock · sede UD1|
  :Validar correo, clave y rol
  y entregar el token;
  note right: El token se guarda 4 minutos
  |RepuAuto · sede Bucaramanga|
else (sí)
endif
:Pedir las facturas del rango:
GET /api/facturas con el token;
|PC Stock · sede UD1|
:Validar el token y responder
sus ventas y compras en JSON;
|RepuAuto · sede Bucaramanga|
if (¿La otra sede
respondió bien?) then (sí)
  :Juntar las facturas de las dos sedes,
  aplicar los filtros y sumar por sede;
  |Administrador|
  :Ver los totales por sede,
  el consolidado y las facturas;
  stop
else (no)
  |RepuAuto · sede Bucaramanga|
  :Preparar el aviso con la causa
  y dejar solo las facturas de esta sede;
  note right
    Causas que el aviso distingue:
    * el servidor o el túnel de ngrok está apagado;
    * la otra sede rechazó el usuario o la clave;
    * respondió datos que no se entienden.
  end note
  |Administrador|
  :Ver el aviso y las facturas
  de Bucaramanga;
  stop
endif
@enduml
"""


if __name__ == "__main__":
    (CARPETA / "actividades_consolidado.svg").write_text(dibujar(), encoding="utf-8")
    (CARPETA / "actividades_consolidado.puml").write_text(PLANTUML, encoding="utf-8")
    print(f"Listo: {len(ACTIVIDADES)} actividades y decisiones en {len(CARRILES)} carriles.")
