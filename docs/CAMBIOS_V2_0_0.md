# Cambios v2.0.0 — Evaluación inicial interactiva real

## Objetivo

La evaluación inicial deja de ser una autoestimación con botones 0–6.
Ahora funciona como una clase/evaluación real: el profesor pregunta, el alumno responde, el sistema corrige y explica.

## Añadido

- Evaluación inicial pregunta por pregunta.
- Preguntas y respuestas barajadas en cada intento.
- Feedback inmediato del profesor.
- Corrección visual:
  - respuesta correcta en verde;
  - respuesta incorrecta en rojo.
- Barra de progreso de evaluación.
- Botones:
  - Leer pregunta;
  - Siguiente pregunta;
  - Reiniciar evaluación;
  - Volver al inicio.
- Guardado de resumen en:

```text
data/evaluacion_inicial.json
```

## Flujo nuevo

1. El alumno entra en Evaluación inicial.
2. El profesor presenta la prueba.
3. Se muestra una pregunta.
4. El alumno elige una opción.
5. El profesor corrige y explica.
6. Se desbloquea “Siguiente pregunta”.
7. Al terminar, se calcula el nivel y se entra al estudio.

## Entrega

ZIP sin carpeta `voices`.
