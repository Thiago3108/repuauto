# Cómo trabajamos

## Flujo de una tarea

1. Toma tu tarjeta en Trello y pásala a **En progreso**.
2. Actualiza `main` y crea una rama para la tarea:
   ```bash
   git switch main
   git pull
   git switch -c feature/US-02-crud-clientes
   ```
3. Haz commits que empiecen con el código de la tarea: `US-02 T2: formulario de clientes`.
   Lo que no es una tarea del backlog empieza con `chore:`.
4. Sube la rama y abre un pull request hacia `main`. Pasa la tarjeta a **En revisión**.
5. Otro integrante lo revisa y lo aprueba. Las pruebas automáticas deben pasar.
6. Se fusiona con **Squash and merge** y se borra la rama.

Nadie sube cambios directo a `main`: la rama está protegida.

## Definición de terminado

Una tarea está terminada cuando:

- su pull request fue aprobado y fusionado;
- las pruebas pasan en GitHub;
- su tarjeta está en **Hecho**.

Solo entonces se anotan sus puntos en el Excel, en la semana en que se terminó.
Cada viernes, cada uno actualiza sus tarjetas, el estado y las horas reales de sus tareas.

## Base de datos

- Las tablas nunca se crean ni se cambian a mano: siempre con una migración.
- Los modelos van en `app/models/`, un archivo por grupo de tablas, con los nombres exactos
  de `docs/diagramas/repuauto_bd.dbml`, y se importan en `app/models/__init__.py`.
- Las restricciones CHECK llevan el nombre del DBML (`chk_repuesto_stock`, etc.).

### Para crear o cambiar tablas

```bash
git switch main && git pull     # trae las migraciones de los demás
flask db upgrade                # aplícalas en tu base
git switch -c feature/US-04-tablas-repuesto
# escribe o cambia el modelo
flask db migrate -m "US-04 T1: tablas de repuestos"
flask db upgrade
```

- Revisa el archivo que se generó en `migrations/versions/` antes de hacer commit.
- Una migración por pull request.
- Si antes de fusionar tu pull request entró otra migración a `main`, borra la tuya,
  actualiza tu rama y vuelve a generarla. Las pruebas automáticas fallan si quedan dos
  migraciones en paralelo.

### Orden en el sprint 1

Cada una se fusiona antes de generar la siguiente, porque las tablas dependen entre sí:

1. `usuario.py` (rol, usuario): US-01 T1
2. `repuesto.py` (categoria, marca_repuesto, repuesto): US-04 T1
3. `cliente.py` (cliente): US-02 T1
4. `vehiculo.py` (marca_vehiculo, vehiculo, repuesto_vehiculo): US-03 T1

### Estilo de los modelos

```python
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class Categoria(db.Model):
    __tablename__ = "categoria"

    id_categoria: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(db.String(60), unique=True)
```

## Datos iniciales

Los catálogos (roles, estados de venta, categorías, marcas) se cargan con `flask seed`.
Quien crea la tabla agrega su función en `app/cli.py`, marcada con `@semilla`, y la hace
segura para correr varias veces: primero revisa si el dato ya existe.

## Versiones

Al cerrar cada sprint se etiqueta `main`: `v0.1-sprint1`, `v0.2-sprint2`, `v1.0-sprint3`.
