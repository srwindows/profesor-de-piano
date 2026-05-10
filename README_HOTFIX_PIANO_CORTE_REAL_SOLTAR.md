# Hotfix: piano virtual no vuelve a sonar al soltar

Este hotfix corrige el problema por el que el piano virtual parecía volver a disparar la nota al soltar el ratón.

## Cambios

- `app/ui/ventana_principal.py`
  - `_nota_off()` ahora ignora releases duplicados si la nota ya no estaba activa.
  - El release del piano virtual corta el audio de forma inmediata.
  - Se mantiene el envío MIDI `note_off` para que un dispositivo externo no deje notas colgadas.

- `app/audio/audio_engine.py`
  - `note_off(..., release_segundos=0)` ahora corta la voz sin cola.
  - Nuevo método `cortar_nota(nota, limpiar_cola=True)` para el piano virtual educativo.
  - Al cortar desde el piano virtual se limpian delay y memoria de reverb para que no parezca una segunda pulsación.

## Verificación

```bash
python3 -m py_compile app/audio/audio_engine.py app/ui/piano_virtual.py app/ui/ventana_principal.py
python3 -m compileall -q app
```
