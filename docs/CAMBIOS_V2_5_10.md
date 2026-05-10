# v2.5.10 — consola limpia en desconexión de botones

- Se corrige el warning de PySide6:
  `RuntimeWarning: Failed to disconnect (None) from signal "clicked()"`.
- El warning aparecía al intentar desconectar botones sin conexiones activas.
- No era un fallo funcional, pero ensuciaba la consola.
- Se modifica `_desconectar_boton()` para comprobar receptores y silenciar ese warning concreto.
