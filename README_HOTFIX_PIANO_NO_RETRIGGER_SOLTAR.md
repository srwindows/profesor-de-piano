# Hotfix — Piano virtual sin segundo disparo al soltar

Corrección aplicada sobre la versión `profesor_piano_v4_1_15_hotfix_partitura_docente_5_niveles`.

## Problema corregido

Al pulsar una tecla del piano virtual debía sonar la nota pulsada, pero al soltar la tecla se percibía un nuevo disparo/ataque de la misma nota.

## Cambios

- `app/ui/piano_virtual.py`
  - `mouseReleaseEvent()` ahora solo emite `nota_soltada`.
  - Se aceptan explícitamente los eventos de ratón para evitar propagaciones raras.
  - Soltar una tecla no puede volver a emitir `nota_pulsada`.

- `app/ui/ventana_principal.py`
  - Añadido control de notas activas del piano virtual.
  - Se ignoran pulsaciones duplicadas de la misma tecla mientras siga activa.
  - Al soltar, se libera la nota con una cola corta y controlada.

- `app/audio/audio_engine.py`
  - `note_off()` acepta `release_segundos` opcional.
  - Las demos y secuencias conservan la liberación general.
  - El piano virtual usa una liberación breve para que el apagado no se perciba como una segunda pulsación.

## Comprobación

```bash
python3 -m py_compile app/audio/audio_engine.py app/ui/piano_virtual.py app/ui/ventana_principal.py
python3 -m compileall -q app
```
