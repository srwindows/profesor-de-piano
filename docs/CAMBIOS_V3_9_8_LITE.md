# v3.9.8 — Entrada MIDI del alumno aplicada a la lectura en pentagrama

## Añadido

Los retos de la pizarra ya pueden evaluarse con el teclado MIDI externo del alumno.

## Qué cambia

Hasta ahora la pizarra podía pedir notas al piano virtual.
Ahora también acepta entrada MIDI real:

```text
Partitura → Leer punto actual → Tocar en piano / Tocar secuencia → tocar en teclado MIDI
```

## Flujo docente

```text
profesor explica pentagrama
↓
pizarra señala nota o secuencia
↓
piano virtual resalta
↓
alumno toca en teclado MIDI
↓
profesor valida nota o secuencia
```

## Estadística inicial

Se guardan contadores básicos en memoria:

- aciertos MIDI de lectura;
- errores MIDI de lectura.

Se muestran en la etiqueta superior de MIDI.

## Sigue siendo Lite

Sin IA pesada, sin Qwen, sin nube, sin modelos y sin carpeta voices.
