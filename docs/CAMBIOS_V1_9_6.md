# Cambios v1.9.6 — Práctica interactiva Nivel 0

## Objetivo
Convertir la teoría del Nivel 0 en práctica real sobre el piano virtual o teclado MIDI.

## Cambios principales

- Añadidos ejercicios prácticos iniciales de Nivel 0 dentro del nivel `inicial`:
  - localizar Do;
  - localizar Re;
  - localizar Mi;
  - tocar la secuencia Do-Re-Mi;
  - tocar la secuencia Do-Re-Mi-Fa-Sol;
  - confirmar el patrón de dos teclas negras.

- Nuevo tipo de ejercicio:
  - `midi_secuencia`

- El alumno puede practicar secuencias tocando en:
  - piano virtual de la pantalla;
  - teclado MIDI externo;
  - entrada escrita, por ejemplo `do-re-mi`.

- En modo práctica:
  - no cuenta como fallo;
  - el profesor indica si la secuencia va bien;
  - si hay error, borra la secuencia para repetir limpio.

- En modo ejercicio evaluable:
  - la secuencia se corrige al completarse;
  - si acierta, avanza al siguiente ejercicio;
  - si falla, vuelve a práctica guiada.

- Añadido botón:
  - `Borrar respuesta`

- El botón `Continuar progreso` ahora puede iniciar la práctica inicial si el Nivel 0 ya estaba superado en `data/progreso_alumno.json`.

## Archivos modificados

- `app/ui/ventana_principal.py`
- `app/ui/pantalla_inicio.py`
- `app/core/profesor_didactico.py`
- `app/config.py`
- `data/ejercicios.json`

## Nota
El ZIP se entrega sin carpeta de voces.
