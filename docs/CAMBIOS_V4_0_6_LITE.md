# v4.0.6 — Historial pedagógico del alumno

## Añadido

Se añade el módulo:

```text
app/core/historial_alumno.py
```

## Qué guarda

El profesor empieza a construir un expediente pedagógico:

- progreso;
- clases superadas;
- ejercicios superados;
- exámenes de clase;
- eventos MIDI;
- aciertos y errores;
- velocity media;
- fallos de pulso;
- notas recurrentes falladas;
- recomendaciones;
- sesiones por fecha.

## Ruta

```text
data/alumnos/<alumno_id>/
```

Con archivos:

```text
perfil.json
progreso.json
historial_clases.json
historial_midi.json
errores_recurrentes.json
recomendaciones.json
sesiones/YYYY-MM-DD.json
```

## Integración

- El profesor consulta el historial al presentar la lección.
- Los exámenes de clase se registran.
- Los ejercicios se registran.
- La entrada MIDI y el piano virtual empiezan a alimentar el historial.
- Los errores de pulso y lectura crean recomendaciones.

## Objetivo

Que el profesor no trate todas las clases como si el alumno empezara de cero, sino que pueda adaptar repasos y correcciones.
