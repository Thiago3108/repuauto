# API REST de RepuAuto

La API entrega las **facturas de venta y de compra** de esta sede en JSON, para que el aplicativo consolidador las junte con las de la otra sede (grupo UD1). Está hecha con el mismo Flask de la app, en el módulo `app/api/`, y usa las mismas reglas de negocio.

- **Dirección base:** `http://127.0.0.1:5000/api` cuando la app corre con `flask run`.
- **Formato:** todo es JSON, también los errores: `{"error": "mensaje"}`.
- **Acceso:** solo cuentas de **administrador**, con un token que se pide en `/api/login`.

## 1. Iniciar sesión: `POST /api/login`

```bash
curl -X POST http://127.0.0.1:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"correo": "admin@repuauto.com", "clave": "tu-clave"}'
```

Respuesta:

```json
{
  "token": "eyJpZCI6MTN9.Zx...",
  "tipo": "Bearer",
  "expira_en": 28800,
  "usuario": {"nombre": "Administrador", "rol": "administrador"}
}
```

`expira_en` está en segundos (8 horas). Cuando el token vence, se pide otro.

## 2. Consultar facturas: `GET /api/facturas`

Cada petición lleva el token en el encabezado `Authorization`:

```bash
curl "http://127.0.0.1:5000/api/facturas?desde=2026-10-01&hasta=2026-10-31" \
  -H "Authorization: Bearer EL_TOKEN"
```

| Parámetro | Obligatorio | Qué es |
|---|---|---|
| `desde` | No | Fecha inicial `AAAA-MM-DD`. Si falta, el primer día del mes actual |
| `hasta` | No | Fecha final `AAAA-MM-DD`, incluida completa. Si falta, hoy |
| `tipo` | No | `venta` o `compra`. Si falta, trae las dos |

Respuesta:

```json
{
  "sucursal": "Bucaramanga",
  "desde": "2026-10-01",
  "hasta": "2026-10-31",
  "moneda": "COP",
  "iva_porcentaje": 19,
  "resumen": {
    "venta": {"cantidad": 1, "subtotal": "100000.00", "iva": "19000.00", "total": "119000.00"},
    "compra": {"cantidad": 1, "subtotal": "567226.89", "iva": "107773.11", "total": "675000.00"}
  },
  "facturas": [
    {
      "tipo": "compra",
      "numero": "C-000045",
      "fecha": "2026-10-04T09:30:00-05:00",
      "tercero": {"documento": "900123456-7", "nombre": "Autopartes del Oriente S.A.S."},
      "subtotal": "567226.89",
      "iva": "107773.11",
      "total": "675000.00"
    },
    {
      "tipo": "venta",
      "numero": "V-000123",
      "fecha": "2026-10-30T10:15:00-05:00",
      "tercero": {"documento": "1098000001", "nombre": "Carlos Andrés Rueda Pinzón"},
      "subtotal": "100000.00",
      "iva": "19000.00",
      "total": "119000.00"
    }
  ]
}
```

Reglas de los datos:

- **Ventas:** solo las **Completadas**. Las Pendientes no se han pagado y las Canceladas devolvieron el stock, igual que en los reportes.
- **Compras:** todas, porque suman al stock apenas se registran.
- **Tercero:** en las ventas es el cliente, con su cédula; en las compras es el proveedor, con su NIT.
- **Número:** `V-` para ventas y `C-` para compras, seguido del número con 6 dígitos.
- **IVA:** va **incluido** en el total: `subtotal = total / 1,19` e `iva = total − subtotal`. Los dos siempre suman el total exacto.
- **Dinero:** texto con 2 decimales, para no perder centavos.
- **Fechas:** formato ISO con la hora de Colombia (`-05:00`).
- **Orden:** de la factura más antigua a la más reciente.

## 3. Errores

| Código | Cuándo |
|---|---|
| `400` | Falta el correo o la clave, una fecha está mal escrita, `desde` va después de `hasta` o el `tipo` no existe |
| `401` | Correo o clave incorrectos, falta el token, el token fue alterado, ya venció o la cuenta fue desactivada |
| `403` | La cuenta no es de administrador |
| `404` / `405` | La ruta no existe o el método no es el correcto |

## 4. Configuración (opcional, en el `.env`)

| Variable | Por defecto | Qué cambia |
|---|---|---|
| `API_SUCURSAL` | `Bucaramanga` | El nombre de la sede en las respuestas |
| `API_IVA` | `19` | El porcentaje de IVA incluido en los precios |
| `API_TOKEN_HORAS` | `8` | Cuántas horas dura un token |

Los tokens se firman con la `SECRET_KEY`: si se cambia, los tokens que ya se entregaron dejan de servir.

## 5. Consolidado de sedes (`/consolidado/`)

Es la página que junta las dos sedes. La ve solo el administrador, en el menú **Consolidado de sedes**. Muestra:

- los totales de cada sede y del consolidado: ventas, compras, IVA y la diferencia;
- todas las facturas de las dos sedes, de la más reciente a la más antigua;
- filtros por rango de fechas, tipo (venta o compra), sede y tercero (nombre o documento, sin importar tildes).

Las facturas de RepuAuto salen de la base de datos con el formato de la sección 2. Las de la otra sede se piden por HTTP a su API cada vez que se abre la página. Si la otra sede no responde, la página muestra un aviso y trae solo las de RepuAuto.

### Configuración en el `.env` de RepuAuto

UD1 implementó nuestro mismo formato y publica su API con ngrok en un dominio fijo. Con la dirección y la cuenta que nos mandan por privado:

```
SEDE_REMOTA_NOMBRE=Sede UD1
SEDE_REMOTA_URL=https://SU-DOMINIO.ngrok-free.dev/api
SEDE_REMOTA_TIPO=repuauto
SEDE_REMOTA_USUARIO=correo-de-la-cuenta-que-nos-dan
SEDE_REMOTA_CLAVE=su-clave
```

Después de cambiar el `.env`, se reinicia `flask run`. Las pruebas (`pytest`) nunca se conectan a la otra sede, aunque el `.env` la tenga.

- RepuAuto manda el encabezado `ngrok-skip-browser-warning` para que ngrok no responda con su página de aviso en lugar del JSON.
- Si la otra sede no responde, el aviso de la página dice por qué: servidor apagado, clave equivocada, dirección de ngrok vieja, etc.

### Respaldo: la API anterior de UD1 (`SEDE_REMOTA_TIPO=ud1`)

Antes de que UD1 implementara nuestro formato, RepuAuto ya sabía leer su API de Django REST y traducirla (`app/consolidado/sedes.py`). Se deja por si hace falta:

| Dato | De dónde sale en UD1 |
|---|---|
| Login | `POST /api/auth/login/` con `username` y `password`; el token es `access` (dura 5 minutos; RepuAuto lo guarda 4 para no pasar su límite de 10 inicios de sesión por minuto) |
| Ventas | `GET /api/ventas/`, solo las de estado `activa`. Número `V-` + `id_venta` |
| Cliente de la venta | `GET /api/clientes/`: `documento`, `nombres` y `apellidos` |
| Compras | `GET /api/lotes/`: cada lote es una factura de compra con total = `cantidad × costo_unitario`. Número `L-` + `id_lote` |
| Proveedor de la compra | `GET /api/proveedores/`: `nombre` (no guardan NIT) |
| Fechas | Su API no filtra por fechas: RepuAuto filtra después de recibir los datos |

## 6. Publicar nuestra API con ngrok (para que UD1 la consulte)

El grupo UD1 consulta nuestras facturas desde su pantalla **Sedes** de PC Stock. Para que nos alcance desde internet se usa ngrok:

1. **Una sola vez:** crear la cuenta en [ngrok.com](https://ngrok.com), instalarlo (`sudo snap install ngrok` en Ubuntu, versión 3.28 o más nueva), correr `ngrok config add-authtoken SU_TOKEN` y copiar el **dominio fijo gratis** del panel (*Domains*), algo como `nombre-nombre-nombre.ngrok-free.dev`.
2. **Una sola vez:** crear una cuenta de administrador solo para la integración y mandarles el correo y la clave **por mensaje privado**:
   ```bash
   flask crear-admin integracion@repuauto.com --nombre "Integración UD1"
   ```
   La contraseña se pide dos veces y no se muestra en pantalla.
3. **Cada vez (prueba y sustentación),** con dos terminales abiertas:
   ```bash
   # Terminal 1: la app SIN modo de depuración, porque ngrok la publica en internet
   flask --no-debug run
   # Terminal 2: el túnel con el dominio fijo
   ngrok http --url=SU-DOMINIO.ngrok-free.dev 5000
   ```
4. **Comprobar:** abrir `https://SU-DOMINIO.ngrok-free.dev/api/facturas` en el navegador. Después del aviso de ngrok debe salir `{"error": "Falta el token..."}`.

**Ojo:** ngrok publica **toda la app**, no solo la API: cualquiera con la dirección ve la pantalla de iniciar sesión. Por eso:
- nunca se arranca con el modo de depuración (`.flaskenv` lo activa; `--no-debug` lo apaga);
- a UD1 se le da la cuenta de integración, no la del administrador principal. Si una clave se compartió por error, se cambia con `flask cambiar-clave CORREO`;
- se cierra ngrok (`Ctrl+C` en la terminal 2) cuando no se esté usando.

## 7. Estado del acuerdo con el grupo UD1

- UD1 implementó **nuestro mismo formato** (`POST /api/login` con `correo` y `clave`, `GET /api/facturas`), así que en RepuAuto se usa `SEDE_REMOTA_TIPO=repuauto` con la dirección de su API. El tipo `ud1` (su API anterior de Django) queda como respaldo.
- Su dirección y la cuenta de administrador para consultarla nos las mandan por privado.
- Falta confirmar el IVA (19 % incluido) y el nombre de cada sede.
