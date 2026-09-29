# Guía de inicio — RepuAuto

Pasos para dejar tu computador listo: instalar las herramientas, crear las bases de datos, clonar el proyecto y arrancarlo. Sirve para **Windows** y para **Linux**. Cuando un paso cambia entre los dos, se indica.

- En **Windows**, los comandos se escriben en **PowerShell**, que puede ser la terminal de VS Code.
- En **Linux**, se escriben en la terminal del sistema o en la de VS Code. Los ejemplos son para Ubuntu y derivados (Linux Mint, Pop!_OS). En otras distribuciones cambia el gestor de paquetes.

> **¿Ya tienes Git y VS Code?** Salta al paso 1.3. Te faltan Python 3.12 y PostgreSQL 18.

## 0. Acceso al repositorio y a Trello

1. Necesitas una cuenta de GitHub.
2. Acepta la invitación de colaborador que te llegó por correo, o entra a https://github.com/Thiago3108/repuauto/invitations. Sin aceptarla puedes descargar el repositorio, pero no subir cambios.
3. Acepta la invitación al tablero de **Trello** que te llegó por el grupo. Ahí se lleva el avance de cada tarea ([guía de Trello](docs/guias/TRELLO.md)).
4. Pide el Excel **Scrum_Trace_RepuAuto** si no lo tienes. Ahí están el backlog, los criterios de aceptación de cada historia y el burndown.

## 1. Instalar las herramientas

| Herramienta | Para qué |
|---|---|
| Git | Control de versiones |
| VS Code, con sus extensiones | Editor |
| Python 3.12 | Ejecutar la app. Es la misma versión que usa el CI |
| PostgreSQL 18 | Base de datos. Todo el equipo usa la misma versión mayor que el CI |
| pgAdmin 4 | Ver las tablas y los datos, y ejecutar SQL con ventanas |

**No hace falta Docker.** Flask, SQLAlchemy, pytest y el resto se instalan dentro del proyecto con `pip` en el paso 4.

### 1.1 Git

- **Windows:** descárgalo de https://git-scm.com/download/win e instálalo con las opciones por defecto.
- **Linux:** `sudo apt install git`

### 1.2 VS Code

Descárgalo de https://code.visualstudio.com. En Linux puedes instalar el `.deb` o usar `sudo snap install code --classic`.

Instala estas extensiones desde la barra lateral (**Extensions**):

- **Python** (Microsoft): te da el autocompletado y permite correr las pruebas.
- **Jinja** (wholroyd): colorea las plantillas de `app/templates/`.

Después de clonar el repo, abre la paleta con `Ctrl+Shift+P`, escribe **Python: Select Interpreter** y elige el que está en `.venv`.

### 1.3 Python 3.12

- **Windows:** descárgalo de https://www.python.org/downloads/ (la versión 3.12.x). En la primera pantalla del instalador marca **Add python.exe to PATH**. Para comprobarlo, `py -3.12 --version` debe mostrar `Python 3.12.x`.
- **Linux:** Ubuntu 24.04 ya trae Python 3.12. Instala además el módulo de entornos virtuales:

  ```bash
  sudo apt install python3.12 python3.12-venv
  ```

  Si tu distribución no tiene `python3.12`, pregunta en el grupo antes de instalar otra versión.

### 1.4 PostgreSQL 18 y pgAdmin

- **Windows:**
  1. Descarga el instalador de EDB para la versión **18** en https://www.postgresql.org/download/windows/.
  2. En los componentes, deja marcados **PostgreSQL Server**, **pgAdmin 4** y **Command Line Tools**. No hace falta Stack Builder.
  3. Te pedirá una contraseña para el superusuario `postgres`. **Anótala**, porque la vas a necesitar en el paso 3.
  4. Deja el puerto **5432**.

  PostgreSQL queda como un servicio que arranca solo con Windows.

- **Linux:** los repositorios de Ubuntu pueden traer una versión más vieja. Por eso se usa el repositorio oficial de PostgreSQL:

  ```bash
  sudo apt install -y postgresql-common
  sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
  sudo apt install -y postgresql-18
  ```

  El servicio arranca solo. Para ver si está encendido, usa `systemctl status postgresql`.

  pgAdmin es opcional en Linux, porque todo se puede hacer con `psql`. Si lo quieres, sigue las instrucciones de https://www.pgadmin.org/download/pgadmin-4-apt/.

### Verificar

Cierra VS Code y las terminales, y vuelve a abrirlos para que reconozcan lo que instalaste. Luego:

| Comando | Linux | Windows |
|---|---|---|
| Git | `git --version` | `git --version` |
| Python | `python3.12 --version` | `py -3.12 --version` |
| PostgreSQL | `psql --version` | `& "C:\Program Files\PostgreSQL\18\bin\psql.exe" --version` |

La versión de PostgreSQL debe empezar por **18**. Python debe ser **3.12.x**.

## 2. Configurar Git (una sola vez)

Usa el **correo de tu cuenta de GitHub**. Así tus commits aparecen a tu nombre y cuentan en las [evidencias de participación](EVIDENCIAS.md):

```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu-correo@ejemplo.com"
git config --global pull.rebase false
git config --global core.editor "code --wait"
git config --global init.defaultBranch main
```

- **`pull.rebase false`:** cuando tu rama y la de GitHub se separan, git las une con un commit de unión. Sin esto, se detiene con el error `Need to specify how to reconcile divergent branches`.
- **`core.editor "code --wait"`:** cuando git necesita un mensaje, abre una pestaña en VS Code en lugar de Vim. Revisa el mensaje, cierra la pestaña y git continúa.

**Solo en Windows**, para que los finales de línea no aparezcan como cambios en todos los archivos:

```powershell
git config --global core.autocrlf true
```

## 3. Crear las bases de datos (una sola vez)

La app usa dos bases de datos:

- **`repuauto`** es la que usas para trabajar;
- **`repuauto_test`** es la de las pruebas, y **se borra en cada corrida de `pytest`**. Por eso son dos.

Entra a PostgreSQL como superusuario:

- **Linux:** `sudo -u postgres psql`
- **Windows:** abre pgAdmin, conéctate al servidor con la contraseña de `postgres`, haz clic derecho en **Databases → Query Tool** y ejecuta las sentencias **una por una**, seleccionando cada línea y presionando `F5`.

Cambia `TU_CLAVE` por una contraseña tuya, **solo con letras y números**. Los símbolos como `@`, `:` o `/` rompen la URL del `.env`.

```sql
CREATE USER repuauto WITH PASSWORD 'TU_CLAVE';
CREATE DATABASE repuauto OWNER repuauto;
CREATE DATABASE repuauto_test OWNER repuauto;
```

En Linux, sal de `psql` con `\q`.

## 4. Clonar el repositorio y crear el entorno

Elige una carpeta donde guardar el proyecto, sin tildes ni espacios si puedes. Luego:

- **Linux:**

  ```bash
  git clone https://github.com/Thiago3108/repuauto.git
  cd repuauto
  python3.12 -m venv .venv
  source .venv/bin/activate
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
  ```

- **Windows (PowerShell):**

  ```powershell
  git clone https://github.com/Thiago3108/repuauto.git
  cd repuauto
  py -3.12 -m venv .venv
  .venv\Scripts\Activate.ps1
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
  ```

  Si PowerShell dice que *la ejecución de scripts está deshabilitada*, ejecuta una vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, responde `S` y vuelve a activar el entorno.

Con el entorno activo, la terminal muestra `(.venv)` al inicio de la línea. **Todos los comandos `flask` y `pytest` se ejecutan con el entorno activo.** Cada vez que abras una terminal nueva, actívalo otra vez.

## 5. Crear tu `.env`

El `.env` guarda tus claves. **Nunca se sube al repositorio** porque está en `.gitignore`.

1. Copia la plantilla:
   - **Linux:** `cp .env.example .env`
   - **Windows:** `copy .env.example .env`
2. Genera una clave secreta:

   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

3. Abre `.env` en VS Code y deja algo así, con **tu** clave de PostgreSQL en las dos URL:

   ```
   SECRET_KEY=la-clave-que-generaste
   DATABASE_URL=postgresql+psycopg://repuauto:TU_CLAVE@localhost:5432/repuauto
   TEST_DATABASE_URL=postgresql+psycopg://repuauto:TU_CLAVE@localhost:5432/repuauto_test
   ```

Si falta alguna variable, la app no arranca y el error dice cuál es: `Faltan variables en tu .env: ...`.

`.flaskenv` sí está en el repo. Le dice a Flask dónde está la app (`FLASK_APP=app`) y activa el modo de depuración. No lo modifiques.

## 6. Preparar la base de datos y arrancar

```bash
flask db upgrade
flask seed
flask run
```

| Comando | Qué hace |
|---|---|
| `flask db upgrade` | Crea las tablas o las actualiza según las migraciones de `migrations/versions/` |
| `flask seed` | Carga los datos iniciales: roles, estados de venta, categorías, marcas y el primer administrador. Se puede correr varias veces sin duplicar datos |
| `flask run` | Arranca la app en http://127.0.0.1:5000. Se detiene con `Ctrl+C` |

Mientras no haya tablas, `flask seed` dice `Todavía no hay datos iniciales definidos.`. Eso es normal.

Al abrir http://127.0.0.1:5000 debes ver la página de inicio con el menú lateral. Los módulos que aún no existen muestran la página "En construcción".

Con `FLASK_DEBUG=1`, la app se recarga sola cuando guardas un archivo `.py`. Si cambias una plantilla y no se ve, recarga el navegador con `Ctrl+F5`.

## 7. Correr las pruebas

```bash
pytest
```

Todas deben pasar (`passed`). Las pruebas usan `repuauto_test`: crean las tablas, las usan y las borran. **Nunca pongas la URL de `repuauto` en `TEST_DATABASE_URL`**, porque borrarías tus datos.

Las mismas pruebas corren en GitHub en cada pull request (el **CI**). Si fallan allá, el pull request no se puede unir.

## 8. Cuando traes cambios de `main`

Cada vez que traigas lo nuevo de `main` (ver la [guía de git](GUIA-GIT.md) §2):

```bash
python -m pip install -r requirements.txt
flask db upgrade
flask seed
```

- **`pip install`** solo hace falta si cambió `requirements.txt`, pero no hace daño correrlo siempre.
- **`flask db upgrade`** aplica las migraciones que crearon tus compañeros. Si no lo corres, verás errores como `relation "cliente" does not exist`.
- **`flask seed`** carga los datos iniciales de las tablas nuevas.

## 9. Si algo falla

| Mensaje | Qué pasó | Qué hacer |
|---|---|---|
| `Faltan variables en tu .env: ...` | No existe el `.env` o le falta una línea | Paso 5 |
| `connection refused` o `could not connect to server` | PostgreSQL está apagado | **Linux:** `sudo systemctl start postgresql` · **Windows:** busca **Servicios**, abre `postgresql-x64-18` y dale **Iniciar** |
| `password authentication failed for user "repuauto"` | La clave del `.env` no es la del paso 3 | Corrige el `.env`, o cambia la clave con `ALTER USER repuauto WITH PASSWORD 'nueva';` |
| `database "repuauto_test" does not exist` | Faltó crear la base de pruebas | Paso 3, la última sentencia |
| `relation "..." does not exist` | Faltan migraciones en tu base | `flask db upgrade` |
| `Can't locate revision identified by '...'` | Tu base tiene una migración que ya no existe en el código (por ejemplo, la de una rama que borraste) | Pregunta en el grupo antes de tocar nada. En la [guía de git](GUIA-GIT.md#conflictos-de-migraciones) está cómo arreglarlo |
| `flask: command not found` o `No module named flask` | El entorno virtual no está activo | Actívalo (paso 4) |
| `Error: Could not locate a Flask application` | Estás fuera de la carpeta del repo | `cd repuauto` |
| `Address already in use` | Ya hay un `flask run` abierto | Ciérralo con `Ctrl+C` en la otra terminal, o usa `flask run --port 5001` |

## 10. Antes de programar

1. Lee el [plan de trabajo](PLAN-DE-TRABAJO.md): qué te toca, a quién esperas y cuál es la definición de terminado.
2. Lee la [guía de git](GUIA-GIT.md) para crear tu rama. **Nunca trabajes en `main`.**
3. Revisa en el Excel los criterios de aceptación de tu historia, y en [`repuauto_bd.dbml`](docs/diagramas/repuauto_bd.dbml) las tablas que vas a usar.
4. Pasa tu tarjeta de Trello a **En progreso** ([guía de Trello](docs/guias/TRELLO.md)).

---

_Última actualización: 2026-09-29_
