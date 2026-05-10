# Cambios v2.5.1 — Partitura explicada y metrónomo con sonido real

## Corrección del metrónomo

El metrónomo ya no depende solo de `QApplication.beep()`, que en muchos Linux puede estar silenciado.

Ahora usa primero el motor de audio interno:

```text
AudioEngine.sonido_metronomo()
```

Si el motor de audio no está disponible, hace fallback al beep del sistema.

## Partitura mejorada

La pantalla de Partitura ahora empieza desde cero:

1. Qué es una partitura de piano.
2. Qué significan pentagrama, clave, compás y pulso.
3. Dónde está el DO central en el piano.
4. Cómo se dibuja el DO central con línea adicional.
5. Qué son negra, blanca, redonda y silencio.
6. Cómo se interpretan las figuras con el metrónomo.

## Metrónomo dentro de Partitura

La pantalla Partitura ahora tiene su propio metrónomo visible:

- tempo configurable;
- compás configurable;
- pulso visual;
- casilla Sonido;
- botón iniciar/detener.

## Versión

```text
APP_VERSION = "2.5.1-partitura-clase-metronomo-real"
```
