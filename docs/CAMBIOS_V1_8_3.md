# Cambios v1.8.3 — pausas reales, barra interactiva y parada inmediata

- La narración ya no depende de que Piper interprete las comas: el texto se divide por coma, dos puntos, punto y coma, punto, interrogación y exclamación.
- Cada signo genera silencio real configurable:
  - `voz_pausa_coma_ms`
  - `voz_pausa_punto_ms`
- El reproductor principal de voz pasa a `sounddevice` con bloques pequeños para que Pausa y Stop respondan de forma casi instantánea.
- La barra de progreso del narrador ahora es interactiva: se puede hacer clic o arrastrar para saltar dentro de la narración.
- Se mantiene respaldo con `paplay`, `pw-play` o `aplay` si `sounddevice` falla.
- La carpeta de voces no se incluye en el ZIP. El usuario la añade manualmente para evitar entregas demasiado pesadas.
