"""Modelos de la base de datos (capa de datos).

Reglas:
- Cada grupo de tablas va en su propio archivo, con los nombres exactos de
  docs/diagramas/repuauto_bd.dbml, y se importa en este archivo para que
  Flask-Migrate lo detecte.
- Las tablas nunca se crean ni se cambian a mano: siempre con una migración.

Orden de creación en el sprint 1 (cada migración se fusiona antes de generar la siguiente):
  1. usuario.py   rol, usuario                                  US-01 T1
  2. cliente.py   cliente (depende de usuario)                  US-02 T1
  3. repuesto.py  categoria, marca_repuesto, repuesto           US-04 T1
  4. vehiculo.py  marca_vehiculo, vehiculo, repuesto_vehiculo   US-03 T1
"""
from app.models.usuario import Rol, Usuario  # noqa: F401
from app.models.cliente import Cliente  # noqa: F401
