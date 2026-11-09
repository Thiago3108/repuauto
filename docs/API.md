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

## 5. Pendiente de acordar con el grupo UD1

El formato es la propuesta que se les envió. Falta confirmar con ellos el IVA, la numeración de las facturas, el nombre de cada sede, quién hace el aplicativo consolidador y dónde se despliegan las API. Si se acuerda otro formato, se cambia en `app/api/services.py` y en `tests/test_api.py`.
