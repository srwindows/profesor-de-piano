# Cambios v2.1.2 — Sesión diaria inteligente

## Paso de gigante

Esta versión une todo lo que ya existe en una rutina de estudio real:
teoría, técnica diaria, práctica, repaso IA, plan personalizado y cierre de sesión.

## Añadido

- Nuevo archivo de datos:

```text
data/sesion_diaria.json
```

- Nuevo progreso:

```text
data/progreso_sesion_diaria.json
```

- Nuevo gestor:

```text
app/core/sesion_diaria.py
```

- Nuevo diálogo:

```text
app/ui/dialogo_sesion_diaria.py
```

## Botones nuevos

- **Sesión diaria** en el panel del avatar.
- **Sesión** en la pantalla de estudio.

## La sesión diaria incluye

1. Preparación del alumno.
2. Técnica diaria.
3. Repaso teórico visual.
4. Práctica interactiva.
5. Repaso IA si hubo fallos.
6. Cierre de sesión.

## Funciones

- Barra de progreso de sesión.
- Siguiente paso recomendado.
- Abrir el paso recomendado.
- Marcar siguiente paso completado.
- Reiniciar sesión.
- Abrir Plan alumno desde la sesión.

## Entrega

ZIP sin carpeta `voices`.
