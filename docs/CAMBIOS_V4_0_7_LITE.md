# v4.0.7 — Motor MIDI Pro ligero

## Objetivo

Corregir la principal observación de auditoría: el historial ya existía, pero faltaba una capa Pro que midiera mejor lo que toca el alumno.

## Añadido

```text
app/core/analisis_midi_pro.py
```

## Qué analiza

- nota correcta;
- secuencia;
- acorde;
- velocity;
- tiempo de reacción;
- pulso frente al metrónomo;
- simultaneidad;
- notas sobrantes;
- notas faltantes;
- duración de nota.

## Integración

- VentanaPrincipal instancia `AnalizadorMidiPro`.
- Los retos de pizarra configuran objetivos de nota/secuencia/pulso.
- Los ejercicios de acorde configuran objetivo de acorde.
- Cada entrada MIDI o piano virtual genera diagnóstico Pro.
- El diagnóstico se guarda en el historial pedagógico.
- El historial amplía estadísticas de reacción, simultaneidad, sobrantes y faltantes.

## Sigue siendo Lite

No usa IA pesada, no usa Qwen, no usa GGUF y no añade modelos.
