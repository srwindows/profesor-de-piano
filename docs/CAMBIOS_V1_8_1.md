# Cambios v1.8.1 — voz con arranque rápido

## Problema corregido
Al pulsar Play, la narración tardaba demasiado en empezar porque Piper generaba toda la explicación completa antes de reproducirla y, además, el sistema anterior podía lanzar Piper demasiadas veces para insertar pausas.

## Corrección
- La voz se genera ahora por bloques naturales.
- El primer bloque se reproduce en cuanto está listo.
- Los siguientes bloques se preparan en segundo plano mientras suena la narración.
- Se mantiene la lectura humanizada con signos de puntuación y pausas.
- Se añade caché WAV por bloque para que repetir la misma explicación sea casi inmediato.
- Se precalienta Piper en segundo plano al abrir el programa para reducir el primer arranque.

## Se mantiene
- Play / Pausa / Stop del narrador.
- Barra de progreso con tiempo transcurrido y tiempo faltante.
- Voz chico por defecto.
- Laura disponible.
- Botones de colores sin rojo.
- Piano interactivo real de 88 teclas.
