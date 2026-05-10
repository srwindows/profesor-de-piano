# Cambios v1.9.5 — Evaluaciones aleatorias

## Objetivo
Evitar que el alumno apruebe memorizando siempre la misma posición de las respuestas.

## Cambios aplicados

- La Mini evaluación final del Nivel 0 ahora baraja el orden de las preguntas cada vez que se abre.
- Las respuestas de cada pregunta también se barajan en cada apertura.
- El índice de la respuesta correcta se recalcula automáticamente después de barajar las opciones.
- El informe de corrección sigue mostrando la respuesta correcta y la explicación de repaso.
- Los intentos guardados en `data/progreso_alumno.json` indican que la evaluación se hizo con orden aleatorio.
- Las respuestas de comprobación de cada lección guiada también aparecen en orden aleatorio.

## Archivo modificado

- `app/ui/pantalla_inicio.py`

## Nota técnica

El JSON conserva las preguntas y respuestas en un orden editable, pero la interfaz las presenta aleatoriamente en tiempo de ejecución. Así se mantiene fácil de ampliar el contenido sin hacer trampas pedagógicas.
