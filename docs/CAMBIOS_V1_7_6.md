# Cambios v1.7.6

- Arranque defensivo de Qt con renderizado software antes de importar PySide6.
- El audio ya no abre PortAudio automáticamente al arrancar; queda listo y se abre al tocar.
- AudioEngine usa bloque y latencia más seguros por defecto para Debian/Xfce.
- Cierre limpio reforzado: se detiene Piper, reproductor, cámara, MIDI y audio.
- Se mantiene Piper como voz única, chico por defecto, pausas configurables y botones de colores sin rojo.
