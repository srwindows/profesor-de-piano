# Cambios v1.9.3 — Celebraciones y música

Esta versión añade refuerzo positivo al flujo pedagógico:

- Celebración visual al superar una lección guiada.
- Celebración mayor al completar todas las lecciones o superar la mini evaluación del Nivel 0.
- Confeti, serpentinas, estrellas y fuegos artificiales suaves integrados como capa sobre la interfaz.
- Música breve de logro sintetizada en tiempo real desde `AudioEngine`, sin añadir archivos pesados de audio.
- La celebración no bloquea la aplicación y se oculta automáticamente.
- Se conservan las imágenes corregidas de teclado y postura dentro de `assets/teoria/nivel_0/`.
- El ZIP sigue sin incluir carpeta de voces.

## Archivos principales modificados

- `app/ui/celebracion_overlay.py`
- `app/ui/ventana_principal.py`
- `app/ui/pantalla_inicio.py`
- `app/audio/audio_engine.py`
- `app/config.py`

## Nota técnica

La música de celebración se genera por síntesis interna, por lo que no depende de MP3/WAV externos ni aumenta el peso del proyecto.
