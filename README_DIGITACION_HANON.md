# Hotfix digitación Hanon

Implementado sobre la copia subida por el usuario, sin reestructurar la interfaz ni eliminar lógica existente.

## Cambios incluidos

- Se añaden las imágenes de manos proporcionadas por el usuario en `assets/teoria/hanon/`.
- La pizarra Hanon ahora dibuja un panel de digitación sincronizado con el pentagrama vivo.
- En cada nota activa se muestran las dos manos y se resalta el dedo correcto.
- Para Hanon se calcula la digitación base:
  - Mano derecha: `1-2-3-4-5-4-3-2`.
  - Mano izquierda: `5-4-3-2-1-2-3-4`.
- La práctica MIDI y la demo pasan la digitación a la pizarra en tiempo real.
- Los mensajes de práctica indican nota, mano y dedo esperado cuando corresponde.

## Archivos tocados

- `app/ui/pizarra_musical.py`
- `app/ui/ventana_principal.py`
- `assets/teoria/hanon/digitacion_hanon_manos_referencia.png`
- `assets/teoria/hanon/mano_izquierda_digitacion_hanon.png`
- `assets/teoria/hanon/mano_derecha_digitacion_hanon.png`

## Comprobación realizada

- Comprobación de sintaxis con `python3 -m py_compile app/ui/pizarra_musical.py app/ui/ventana_principal.py`.
