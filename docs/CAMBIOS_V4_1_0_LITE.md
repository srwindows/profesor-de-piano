# v4.1.0 — Repertorio MIDI propio para Nivel 1

## Objetivo

Empezar a convertir el Nivel 1 en música real, no solo ejercicios.

## Añadido

Se incorporan 6 archivos MIDI didácticos propios:

```text
assets/midi/nivel_1/tecnica/n1_tecnica_cinco_dedos_do.mid
assets/midi/nivel_1/canciones/cumpleanos_feliz_simplificado_v1.mid
assets/midi/nivel_1/clasicas/oda_alegria_reducida_v1.mid
assets/midi/nivel_1/canciones/frere_jacques_simplificado_v1.mid
assets/midi/nivel_1/canciones/twinkle_simplificado_v1.mid
assets/midi/nivel_1/canciones/vals_didactico_profesor_v1.mid
```

## Legalidad

Estos MIDIs se han creado desde cero como material didáctico propio del proyecto.
No se han descargado archivos MIDI externos.

## Integración

- `data/repertorio.json` incluye las nuevas piezas.
- `data/colecciones/nivel_1/repertorio.json` queda funcional.
- Las clases 26, 27 y 30 del Nivel 1 quedan vinculadas a repertorio MIDI.
- El diálogo de repertorio muestra la ruta MIDI cuando existe.
- Se conserva el panel Diagnóstico Pro.

## Enfoque didáctico

El final del Nivel 1 ya empieza a tener:

```text
ambas manos
canción sencilla
primer contacto clásico
MIDI
metrónomo
diagnóstico Pro
```
