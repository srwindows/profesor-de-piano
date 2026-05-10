# Cambios v2.0.3 — Plan activo con seguimiento

## Objetivo

El plan personalizado ya no es solo una lista de recomendaciones. Ahora se puede seguir como una ruta de trabajo real.

## Añadido

- Seguimiento de pasos del plan:
  - pendiente;
  - completado.
- Barra de progreso del plan.
- Siguiente paso recomendado.
- Botón **Marcar siguiente paso completado**.
- Botón **Reiniciar seguimiento**.
- Celebración al completar un paso del plan.
- Persistencia del estado en:

```text
data/plan_personalizado.json
```

## Archivos modificados

```text
app/core/plan_personalizado.py
app/ui/dialogo_plan_personalizado.py
app/ui/ventana_principal.py
```

## Versión

```text
APP_VERSION = "2.0.3-plan-activo-seguimiento"
```

## Entrega

ZIP sin carpeta `voices`.
