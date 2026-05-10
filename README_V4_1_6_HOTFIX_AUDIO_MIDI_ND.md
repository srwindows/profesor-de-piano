# Profesor de Piano v4.1.6 Lite — Hotfix Audio y MIDI ND

## Ejecutar

```bash
python3 main.py
```

## Si quieres probar sin salida defensiva

```bash
PROFESOR_SALIDA_OS_EXIT=0 python3 main.py
```

## Corrección principal

La Clase 1 Nivel 1 ahora usa un MIDI limpio de mano derecha:

```text
DO RE MI FA SOL FA MI RE DO
```

y el cierre de PortAudio se hace de forma más defensiva.
