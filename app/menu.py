"""Menú lateral de RepuAuto, según la matriz de roles aprobada (decisión D3).

Cada entrada dice a qué vista lleva, qué historia la construye y qué roles la ven.
Cada usuario ve solo las entradas de su rol (menu_para). Ocultar una opción no protege
la vista: cada módulo la protege con @rol_requerido (app/auth/decoradores.py).
"""

TODOS = ("cliente", "vendedor", "administrador")
PERSONAL = ("vendedor", "administrador")
ADMIN = ("administrador",)
CLIENTE = ("cliente",)

# icono es el nombre de un icono de Bootstrap Icons; descripcion sale en la página de inicio.
MENU = [
    {"texto": "Catálogo", "endpoint": "catalogo.index", "historia": "US-05", "roles": TODOS,
     "icono": "search", "descripcion": "Busca repuestos por nombre, código o vehículo."},
    {"texto": "Mis compras", "endpoint": "ventas.mis_compras", "historia": "US-08", "roles": CLIENTE,
     "icono": "bag-check", "descripcion": "Revisa el estado y el historial de tus compras."},
    {"texto": "Ventas", "endpoint": "ventas.index", "historia": "US-06", "roles": PERSONAL,
     "icono": "receipt", "descripcion": "Registra ventas y completa o cancela las pendientes."},
    {"texto": "Clientes", "endpoint": "clientes.index", "historia": "US-02", "roles": PERSONAL,
     "icono": "people", "descripcion": "Registra, busca y actualiza los clientes."},
    {"texto": "Repuestos y stock", "endpoint": "repuestos.index", "historia": "US-04", "roles": PERSONAL,
     "icono": "box-seam", "descripcion": "Consulta precios, existencias y alertas de stock."},
    {"texto": "Vehículos", "endpoint": "vehiculos.index", "historia": "US-03", "roles": ADMIN,
     "icono": "car-front", "descripcion": "Registra vehículos y sus repuestos compatibles."},
    {"texto": "Reportes", "endpoint": "reportes.index", "historia": "US-07", "roles": ADMIN,
     "icono": "bar-chart-line", "descripcion": "Informes de ventas, compras, clientes e inventario."},
    {"texto": "Consolidado de sedes", "endpoint": "consolidado.index", "historia": "Integración", "roles": ADMIN,
     "icono": "buildings", "descripcion": "Facturas e inventario de las dos sedes en un solo lugar."},
    {"texto": "Proveedores y compras", "endpoint": "compras.index", "historia": "US-09", "roles": ADMIN,
     "icono": "truck", "descripcion": "Registra proveedores y las compras que suman al stock."},
    {"texto": "Cuentas y acceso", "endpoint": "auth.index", "historia": "US-01", "roles": ADMIN,
     "icono": "person-gear", "descripcion": "Crea y administra las cuentas de los vendedores."},
]


def menu_para(usuario):
    """Las entradas del menú que puede ver el usuario, según su rol."""
    if not usuario.is_authenticated:
        return []
    return [item for item in MENU if usuario.tiene_rol(*item["roles"])]
