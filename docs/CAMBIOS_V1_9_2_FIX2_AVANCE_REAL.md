# v1.9.2 FIX2 — avance real de lecciones guiadas

Corrección aplicada al bloqueo de la primera lección.

## Problema detectado

Podía ocurrir que `data/progreso_alumno.json` tuviera una lección guardada como superada, pero `leccion_actual_id` siguiera apuntando a esa misma lección. En pantalla se veía:

- `Superadas: 1/6`
- `Actual: Postura al piano...`

Eso generaba sensación de bloqueo porque la lección aparecía superada pero el curso seguía visualmente en la primera.

## Solución

- Añadido salto automático a la primera lección pendiente cuando se entra en Teoría.
- El botón `Siguiente lección` avanza ahora por índice real, no por estados intermedios.
- Si una lección ya estaba superada y se pulsa `Comprobar respuesta`, el sistema no vuelve a bloquear por la opción seleccionada: avanza a la siguiente.
- Añadidos métodos robustos en `app/core/lecciones_guiadas.py`:
  - `indice_de()`
  - `fijar_leccion_actual()`
  - `siguiente_por_indice()`
  - `primera_pendiente_desde_actual()`

## Nota

La carpeta de voces sigue excluida del ZIP.
