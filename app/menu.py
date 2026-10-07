"""Menú lateral de RepuAuto, según la matriz de roles aprobada (decisión D3).

Cada entrada dice a qué vista lleva, qué historia la construye y qué roles la ven.
Cada usuario ve solo las entradas de su rol (menu_para). Ocultar una opción no protege
la vista: cada módulo la protege con @rol_requerido (app/auth/decoradores.py).
US-08 agregará "Mis compras" para el cliente.
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


def menu_para(usuario):
    """Las entradas del menú que puede ver el usuario, según su rol."""
    if not usuario.is_authenticated:
        return []
    return [item for item in MENU if usuario.tiene_rol(*item["roles"])]
