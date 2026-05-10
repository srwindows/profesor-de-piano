# v4.1.5 — Pentagrama vivo sincronizado con MIDI Didáctico / ND

## Cambio principal

Cuando se usa el MIDI Didáctico / ND, el pentagrama ya no queda estático.

Ahora:

```text
nota activa del MIDI
↓
nota resaltada en el pentagrama
↓
misma nota esperada por el Motor MIDI Pro
↓
misma nota marcada en el piano virtual en modo práctica/escucha
↓
profesor explica compás, pulso y nota siguiendo ese flujo
```

## Añadido

```text
data/pentagrama_nd_nivel_1.json
```

## Modificado

```text
app/ui/pizarra_musical.py
app/ui/ventana_principal.py
```

## Qué se ve

- nota actual resaltada fuerte;
- siguiente nota preparada;
- notas pasadas atenuadas;
- compás y pulso activos;
- barra de avance del MIDI;
- texto docente sincronizado.

## Uso

Entra en:

```text
MIDI Didáctico
```

Carga la Clase 1 Nivel 1 o cualquier pieza del repertorio interno. Al usar Escuchar guía, Practicar o Examen, el pentagrama ND se actualiza siguiendo el MIDI.
