# Cambios v1.8.9

## Ejercicios interactivos

- El piano virtual y el teclado MIDI externo usan una entrada común: `procesar_nota_alumno`.
- En ejercicios de tipo `midi_nota`, el programa compara la nota tocada con la solución del ejercicio.
- En fase `Práctica guiada`, los errores no cuentan.
- En fase `Ejercicio evaluable`, aciertos y fallos actualizan progreso, racha y avance.
- Para la lección de Do, vale cualquier octava: C1, C2, C3, C4, C5, C6, C7 o C8, porque se compara la nota base `do`.

## Narrador

- Valores por defecto de pausas:
  - Coma: 250 ms.
  - Punto: 750 ms.

## Entrega

- ZIP sin carpeta de voces. El usuario añade manualmente `voices/`.
