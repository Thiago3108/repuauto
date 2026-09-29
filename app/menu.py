"""Menú lateral de RepuAuto, según la matriz de roles aprobada (decisión D3).

Cada entrada dice a qué vista lleva, qué historia la construye y qué roles la ven.
Por ahora el menú muestra todo: el filtrado por rol lo activa US-01 (control de acceso
por rol) usando el campo "roles". US-08 agregará "Mis compras" para el cliente.
"""

TODOS = ("cliente", "vendedor", "administrador")
PERSONAL = ("vendedor", "administrador")
ADMIN = ("administrador",)

MENU = [
    {"texto": "Catálogo", "endpoint": "catalogo.index", "historia": "US-05", "roles": TODOS},
    {"texto": "Ventas", "endpoint": "ventas.index", "historia": "US-06 y US-08", "roles": PERSONAL},
    {"texto": "Clientes", "endpoint": "clientes.index", "historia": "US-02", "roles": PERSONAL},
    {"texto": "Repuestos y stock", "endpoint": "repuestos.index", "historia": "US-04", "roles": PERSONAL},
    {"texto": "Vehículos", "endpoint": "vehiculos.index", "historia": "US-03", "roles": ADMIN},
    {"texto": "Reportes", "endpoint": "reportes.index", "historia": "US-07", "roles": ADMIN},
    {"texto": "Proveedores y compras", "endpoint": "compras.index", "historia": "US-09", "roles": ADMIN},
    {"texto": "Cuentas y acceso", "endpoint": "auth.index", "historia": "US-01", "roles": ADMIN},
]
