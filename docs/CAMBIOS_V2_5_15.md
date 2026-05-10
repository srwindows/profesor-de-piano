# v2.5.15 — corrección real del botón del título

- Se corrige la causa real de que el profesor dijera `Pestaña`.
- `QPushButton.clicked` enviaba un booleano y la lambda recibía ese valor en lugar del panel.
- Ahora las lambdas absorben `_checked` y conservan el panel correcto.
- También se añade defensa interna: si llega un bool, se recupera el panel integrado activo.
- En Estado alumno, el botón del título debe decir: `Javi, estás en «Estado del alumno»`.
