# Cambios v2.2.0 — Repertorio progresivo guiado

## Paso serio y grande

El curso ya no se queda solo en teoría, técnica y ejercicios: ahora tiene repertorio progresivo.  
La idea es que el alumno aplique lo aprendido en piezas pequeñas, guiadas por fases.

## Añadido

- Nuevo archivo de datos:

```text
data/repertorio.json
```

- Nuevo progreso:

```text
data/progreso_repertorio.json
```

- Nuevo gestor:

```text
app/core/repertorio.py
```

- Nuevo diálogo:

```text
app/ui/dialogo_repertorio.py
```

## Botones nuevos

- **Repertorio** en el panel del avatar.
- **Repertorio** en la pantalla de estudio.

## Piezas incluidas

- Dos negras y un Do.
- Camino de cinco dedos.
- Pulso de paseo.
- Primer acorde de Do.
- Pregunta y respuesta.

## Cada pieza incluye

- nivel;
- objetivo;
- tempo;
- compás;
- mano derecha;
- mano izquierda;
- digitación;
- fases de estudio;
- criterio de superación.

## Integración

- Se añade a la ruta curricular.
- Se añade como paso dentro de la sesión diaria.
- Permite marcar piezas como trabajadas.
- Incluye celebración al trabajar una pieza.

## Entrega

ZIP sin carpeta `voices`.
