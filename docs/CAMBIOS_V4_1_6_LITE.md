# v4.1.6 — Hotfix Audio/PortAudio + MIDI ND Clase 1

## Correcciones

### 1. PortAudio / ALSA / pthread_join

Se refuerza el cierre de audio:

- se detiene primero el MIDI Didáctico;
- se detiene escucha/micrófono bajo demanda;
- se limpia cámara/MIDI;
- se cierra AudioEngine de forma defensiva;
- `main.py` sale por `os._exit()` después del cierre explícito para evitar finalizadores tardíos de PortAudio.

Si se quiere desactivar esta salida defensiva:

```bash
PROFESOR_SALIDA_OS_EXIT=0 python3 main.py
```

### 2. MIDI Clase 1 Nivel 1

El MIDI `n1_tecnica_cinco_dedos_do.mid` se ha corregido para que contenga solo la secuencia de mano derecha:

```text
C4 D4 E4 F4 G4 F4 E4 D4 C4
```

Antes aparecían notas graves de acompañamiento que no correspondían a la clase inicial.

### 3. Pentagrama ND

El pentagrama ND ahora sigue una fuente MIDI coherente con la teoría de la clase.
