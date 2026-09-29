# RepuAuto

Sistema de gestión para una serviteca de repuestos para carro: catálogo con filtro por
vehículo, ventas con control de stock, clientes, compras a proveedores y reportes.

Proyecto de Ingeniería de Software II, UIS 2026. Unidad de desarrollo:
Santiago Martínez, Jhon Sotelo, Jairo Cardozo y David Muñoz.

**Tecnología:** Flask (tres capas, patrón MVC), PostgreSQL, SQLAlchemy con Flask-Migrate,
plantillas Jinja con Bootstrap y pytest.

## Requisitos

- Python 3.12
- PostgreSQL (la misma versión mayor para todo el grupo)
- Git

## Instalación

### 1. Clonar y crear el entorno

Linux:

```bash
git clone https://github.com/Thiago3108/repuauto.git
cd repuauto
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
git clone https://github.com/Thiago3108/repuauto.git
cd repuauto
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Si PowerShell no deja activar el entorno, ejecuta una vez
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

### 2. Crear la base de datos

Entra a PostgreSQL como superusuario: en Linux con `sudo -u postgres psql`; en Windows,
con el Query Tool de pgAdmin. Ejecuta estas sentencias, cambiando `TU_CLAVE` por una
contraseña tuya de solo letras y números. En pgAdmin, ejecútalas una por una.

```sql
CREATE USER repuauto WITH PASSWORD 'TU_CLAVE';
CREATE DATABASE repuauto OWNER repuauto;
CREATE DATABASE repuauto_test OWNER repuauto;
```

### 3. Crear tu `.env`

Copia la plantilla (`cp .env.example .env` en Linux, `copy .env.example .env` en Windows)
y en el `.env`:

- pon tu clave en las dos URL, en lugar de `clave`;
- reemplaza `cambia-esto` por una clave generada con
  `python -c "import secrets; print(secrets.token_hex(32))"`.

El `.env` nunca se sube al repositorio.

### 4. Preparar y correr

```bash
flask db upgrade   # crea o actualiza las tablas
flask seed         # carga los datos iniciales
flask run          # abre http://127.0.0.1:5000
```

Cada vez que traigas cambios de `main`, vuelve a correr `flask db upgrade`.

## Pruebas

```bash
pytest
```

Usan la base `repuauto_test`, que se borra en cada corrida. En GitHub, cada pull request
corre las mismas pruebas automáticamente.

## Estructura

```
app/
├── __init__.py      fábrica create_app()
├── extensions.py    base de datos, migraciones y protección CSRF
├── menu.py          menú por rol
├── cli.py           comando flask seed
├── models/          modelos de la base de datos
├── auth/ … compras/ un módulo por historia: routes.py (controlador) y services.py (negocio)
├── templates/       vistas
└── static/
migrations/          historial de la base de datos
tests/               pruebas
docs/                diagramas (fuentes .puml y .dbml) y actas
```

## Enlaces

- Tablero de tareas (Trello): _pendiente_
- Carpeta del informe y el burndown (Drive): _pendiente_
- Cómo trabajamos: [CONTRIBUTING.md](CONTRIBUTING.md)
