# v4.0.8 — Gestor Pro de entradas del alumno

## Objetivo

Preparar la arquitectura Pro con las cuatro entradas principales:

```text
MIDI
Cámara
Sonido / micrófono
Historial
```

## Regla de consumo

- MIDI: siempre activo, porque consume poco y da información musical continua.
- Historial: siempre activo, porque guarda datos didácticos.
- Cámara: solo bajo petición del profesor y activación voluntaria del alumno.
- Sonido/micrófono: solo bajo petición del profesor y activación voluntaria del alumno.

## Añadido

```text
app/core/entradas_alumno_pro.py
app/audio/audio_input_manager.py
```

## Integración

- Nueva pestaña `Entradas Pro`.
- Botón `Profesor pide cámara`.
- Botón `Profesor pide escucha`.
- Botón `Activar escucha`.
- Botón `Detener escucha`.
- La cámara actual informa al gestor Pro cuando se activa/detiene.
- La escucha analiza solo RMS/pico, sin grabar audio.
- El historial guarda observaciones didácticas, no vídeo/audio.

## Privacidad

Por defecto:

```text
no se graba vídeo
no se graba audio
solo se guardan observaciones pedagógicas
```
