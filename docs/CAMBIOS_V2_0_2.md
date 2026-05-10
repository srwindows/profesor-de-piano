# Cambios v2.0.2 — Plan personalizado del alumno

## Objetivo

Después de la evaluación inicial interactiva, el programa ya no se limita a recomendar un nivel.
Ahora crea un plan personalizado según los fallos detectados.

## Añadido

- Nuevo archivo:

```text
app/core/plan_personalizado.py
```

- Nuevo diálogo:

```text
app/ui/dialogo_plan_personalizado.py
```

- Nuevo JSON generado automáticamente:

```text
data/plan_personalizado.json
```

## Funciones nuevas

- Botón **Plan alumno** en el panel del avatar.
- Botón **Plan alumno** en la pantalla de estudio.
- El plan contiene:
  - nivel recomendado;
  - pasos ordenados;
  - prioridad;
  - motivo pedagógico;
  - acción recomendada.
- Desde el plan se puede:
  - ir a teoría desde cero;
  - ir a práctica del nivel recomendado.

## Entrega

ZIP sin carpeta `voices`.
