<!-- Título del PR: "US-XX TY: qué entrega" (ej.: "US-02 T2: CRUD de clientes").
     Con Squash and merge, el título queda como el mensaje del commit en main. -->

## Qué hace

(una o dos frases)

## Tarjetas de Trello

- US-XX TY · (título de la tarjeta) — (enlace a la tarjeta)

## Cómo probarlo

1. `flask db upgrade` y `flask seed`
2. Entra como ... y abre ...
3. ...

## Definición de terminado

- [ ] Cumple los criterios de aceptación de la historia
- [ ] Tiene pruebas y `pytest` pasa
- [ ] Tablas y columnas iguales al DBML
- [ ] Si trae migración: revisada a mano, `downgrade` probado y una sola cabeza (`flask db heads`)
- [ ] Si trae catálogos: están en `flask seed` y se puede correr dos veces
- [ ] Matriz de trazabilidad actualizada (si cambió una historia, vista o tabla)
- [ ] Casilla del README marcada (si cierra una historia)
