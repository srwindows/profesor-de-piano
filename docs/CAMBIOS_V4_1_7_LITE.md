# v4.1.7 — Hotfix Pizarra Musical

## Error corregido

En v4.1.6 la pizarra musical fallaba al pulsar `Leer punto actual` porque el menú conectaba acciones a métodos que no existían:

```text
_pedir_secuencia_piano
_pedir_pulso_piano
```

El error visible era:

```text
AttributeError: 'PizarraMusicalProfesor' object has no attribute '_pedir_secuencia_piano'
```

## Corrección

Se añaden los métodos faltantes en:

```text
app/ui/pizarra_musical.py
```

## Qué hacen ahora

```text
Tocar secuencia → emite secuencia_piano_solicitada
Tocar con pulso → emite pulso_piano_solicitado
```

Estos eventos ya estaban conectados en `VentanaPrincipal`, por lo que ahora la pizarra vuelve a funcionar con:

- práctica normal;
- secuencia guiada;
- reto con pulso;
- piano virtual;
- teclado MIDI;
- Motor MIDI Pro.
