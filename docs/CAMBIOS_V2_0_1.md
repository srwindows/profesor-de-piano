# Cambios v2.0.1 — Evaluación inicial con diagnóstico

## Objetivo

La evaluación inicial ya era interactiva en la v2.0.0. En esta versión se añade una capa de diagnóstico pedagógico para que el profesor no salte automáticamente al estudio sin explicar el resultado.

## Añadido

- Botón **No lo sé todavía** en cada pregunta.
- Registro detallado de:
  - pregunta;
  - respuesta elegida;
  - respuesta correcta;
  - si fue correcta;
  - categoría pedagógica;
  - explicación.
- Diagnóstico final del profesor.
- Detección de puntos a reforzar.
- Botón **Continuar al nivel recomendado**.
- Botón **Repasar teoría desde cero**.
- La evaluación ya no cambia de pantalla automáticamente tras terminar.
- Guardado ampliado en:

```text
data/evaluacion_inicial.json
```

## Entrega

ZIP sin carpeta `voices`.
