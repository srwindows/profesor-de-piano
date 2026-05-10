# Cambios v1.9.8 — Panel Estado del alumno

## Objetivo

Añadir un panel de seguimiento para que el profesor virtual no solo corrija,
sino que pueda explicar al alumno cómo va, qué falla más y qué debería repasar.

## Añadido

- Nuevo botón **Estado alumno** en la pantalla de estudio.
- Nuevo diálogo `app/ui/dialogo_estado_alumno.py`.
- Panel con avatar integrado.
- Métricas:
  - nivel actual;
  - ejercicios superados;
  - ejercicios fallados;
  - tasa de acierto;
  - racha;
  - repasos pendientes;
  - lecciones guiadas;
  - exámenes aprobados.
- Lista de fallos frecuentes.
- Recomendación pedagógica del profesor.
- Integración con **Repaso IA**:
  - desde el panel se puede pulsar **Iniciar Repaso IA**.

## También

- `APP_VERSION` actualizado a `1.9.8-panel-estado-alumno`.
- `data/lecciones_nivel_0.json` actualizado a `1.9.8-panel-estado-alumno`.
- ZIP entregado sin carpeta de voces.
