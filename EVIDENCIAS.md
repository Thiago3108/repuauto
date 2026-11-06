# Evidencias de participación y trazabilidad — RepuAuto

**Ingeniería de Software II** · Universidad Industrial de Santander · 2026
**Repositorio:** https://github.com/Thiago3108/repuauto · **Tablero:** Trello (por invitación)

Este documento reúne las pruebas de qué hizo cada integrante y cómo se llega de cada historia a su código y a sus pruebas.

**Cómo se llena:**

- Se completa al cerrar cada sprint.
- Cada integrante revisa su fila y agrega sus pull requests.
- Las capturas van en `docs/evidencias/`, con los nombres de la sección 3.

## 1. Participación en el software

### 1.1 Qué hizo cada uno

La columna *Planeado* sale del [plan de trabajo](PLAN-DE-TRABAJO.md#quién-hace-qué). La columna *Lo que hizo* es lo que entró a `main`, según los pull requests. Jhon estuvo hospitalizado desde el 7 de octubre, así que sus tareas las hizo Santiago.

| Integrante | Planeado | Lo que hizo | Pull requests |
|---|---|---|---|
| Santiago Martínez | US-01 completa · US-06 T3 y T4 · US-07 T3 y T4 | US-01 completa · US-06 T3 y T4 · US-07 T3 y T4 · esqueleto de la app, CI y guías · limpieza del repositorio. Cubriendo a Jhon: US-02 completa, US-06 T1, T2 y T5, US-07 T1 y US-09 T2 y T4. En lugar de Jairo: US-07 T2 y US-09 T1 y T3 | #1 a #9, #14 a #17, #19 a #22 |
| Jhon Sotelo | US-02 completa · US-06 T1, T2 y T5 · US-07 T1 · US-09 T2 y T4 | Hospitalizado; sus tareas las hizo Santiago | — |
| Jairo Cardozo | US-04 completa · US-05 T1, T3 y T4 · US-07 T2 · US-09 T1 y T3 | US-04 completa · revisó los PR #2 y #3 | #11, #12, #13 (el #10 se cerró) |
| David Muñoz | US-03 completa · US-05 T2 · US-08 completa | US-03 completa · US-05 completa (también T1, T3 y T4, que eran de Jairo) · US-08 completa · revisó los PR #4 y #5 | #18 |

### 1.2 Commits y pull requests

Los números salen de git y de GitHub, y se actualizan antes de cada entrega:

```bash
git switch main
git pull
git shortlog -sn --no-merges
```

Con *Squash and merge*, cada PR queda en `main` como un commit **a nombre de quien lo abrió**. Por eso es importante que cada uno tenga configurado su nombre y el correo de su cuenta de GitHub ([guía de inicio](GUIA-INICIO.md) §2).

| Integrante | Commits en `main` | Pull requests unidos | Pull requests revisados |
|---|---|---|---|
| Santiago Martínez | 20 | 17 | — |
| Jhon Sotelo | 0 | 0 | 0 |
| Jairo Cardozo | 3 | 3 | 2 (#2 y #3) |
| David Muñoz | 1 | 1 | 2 (#4 y #5) |

Los números cuentan los PR #21 y #22 (US-07 y US-09). Los commits de Santiago incluyen los primeros del repositorio, hechos antes de usar pull requests, y que aparecen a nombre de *Thiago3108*. Desde el 15 de octubre `main` no exige aprobación, por eso los PR posteriores no tienen revisiones.

Los PR de cada uno se ven en `https://github.com/Thiago3108/repuauto/pulls?q=is%3Apr+author%3A<usuario-de-github>`.

## 2. Trazabilidad

Cada historia se sigue desde el Excel hasta el código. La tarjeta de Trello y el PR llevan el mismo código `US-XX TY`, y el título del PR queda como el mensaje del commit en `main` ([guía de git](GUIA-GIT.md) §5). La matriz completa, con los casos de uso, está en el Excel (hoja *Trazabilidad*).

| Historia | Épica | Vistas | Módulo | Pruebas | Responsables | Lo hizo | Pull requests | Terminó en `main` |
|---|---|---|---|---|---|---|---|---|
| US-01 Registro e inicio de sesión | EP-01 | UI-01, UI-02, UI-03, UI-13 | `app/auth` | `tests/test_auth.py` | Santiago | Santiago | #2, #3, #5, #6 | 2026-10-15 |
| US-02 Gestionar clientes | EP-02 | UI-08 | `app/clientes` | `tests/test_clientes.py` | Jhon | Santiago | #4, #7, #8, #9 | 2026-10-15 |
| US-03 Gestionar vehículos | EP-03 | UI-11 | `app/vehiculos` | `tests/test_vehiculos.py` | David | David | #18 | 2026-10-31 |
| US-04 Gestionar repuestos y stock | EP-03 | UI-09, UI-10 | `app/repuestos` | `tests/test_repuestos.py` | Jairo | Jairo | #11, #12, #13 | 2026-10-20 |
| US-05 Catálogo por vehículo | EP-03 | UI-04 | `app/catalogo` | `tests/test_catalogo.py` | Jairo, David | David | #18 | 2026-10-31 |
| US-06 Registrar venta | EP-04 | UI-06, UI-07 | `app/ventas` | `tests/test_ventas.py` | Jhon, Santiago | Santiago | #15, #16, #17 | 2026-10-25 |
| US-07 Generar reportes | EP-05 | UI-12 | `app/reportes` | `tests/test_reportes.py` | Santiago, Jhon, Jairo | Santiago | #19, #20, #21 | 2026-11-05 |
| US-08 Estado e historial de compras | EP-04 | UI-05 | `app/ventas` | `tests/test_historial.py` | David | David | #18 | 2026-10-31 |
| US-09 Compras a proveedores | EP-06 | UI-14 | `app/compras` | `tests/test_compras.py` | Jairo, Jhon | Santiago | #22 | 2026-11-05 |

La matriz del Excel (hoja *Trazabilidad*) sigue igual: las historias, vistas, tablas y módulos se construyeron como se diseñaron. Lo que cambió fue quién hizo cada tarea, y eso queda en esta tabla.

## 3. Capturas por sprint

| Sprint | Etiqueta en git | Capturas en `docs/evidencias/` |
|---|---|---|
| 1 | `v0.1-sprint1` | `sprint-1-trello.png` · `sprint-1-burndown.png` · `sprint-1-ci.png` |
| 2 | `v0.2-sprint2` | `sprint-2-trello.png` · `sprint-2-burndown.png` · `sprint-2-ci.png` |
| 3 | `v1.0-sprint3` | `sprint-3-trello.png` · `sprint-3-burndown.png` · `sprint-3-ci.png` |

- **`trello`:** el tablero al cerrar el sprint.
- **`burndown`:** la gráfica del Excel.
- **`ci`:** la pestaña **Actions** de GitHub con las corridas en verde.

## 4. Retrospectivas y actas

- Las retrospectivas están en el [plan de trabajo](PLAN-DE-TRABAJO.md#retrospectivas).
- Las actas de las reuniones están en [`docs/actas/`](docs/actas/).

---

_Última actualización: 2026-11-05_
