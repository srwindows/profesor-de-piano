# Cambios v1.7.4

## Voz Piper

- El avatar usa **chico por defecto** porque la voz actual configurada como chico es la que mejor resultado da.
- La velocidad de voz ahora sí se aplica a Piper mediante `--length-scale`.
- La escala de velocidad queda así:
  - `50 %` = lento
  - `100 %` = natural
  - `220 %` = rápido
- El volumen de voz también se aplica sobre el WAV generado antes de reproducirlo.
- La configuración se guarda en `data/ajustes_usuario.json`.

## Nota técnica

Piper no usa un parámetro `speed`. Para cambiar la velocidad real hay que usar `--length-scale`:

- `length_scale > 1.0` habla más lento.
- `length_scale = 1.0` habla natural.
- `length_scale < 1.0` habla más rápido.
