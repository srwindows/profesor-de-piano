# Hotfix: piano interactivo global

Este hotfix corrige que el piano interactivo solo estuviera dentro de la pantalla de estudio y desapareciera al cambiar a pantallas prácticas como Hanon.

## Cambios aplicados

- El piano virtual de 88 teclas se crea una sola vez como widget global bajo el área central.
- `self.piano` se mantiene como referencia única para no duplicar la lógica de MIDI, evaluación, resaltado docente ni corrección.
- El piano queda visible en pantallas prácticas: estudio, evaluación, Hanon, Partitura, Pulso, Repertorio, Técnica diaria y paneles integrados.
- La portada/inicio no muestra el piano porque no es una pantalla de práctica.
- La pantalla Hanon ya no fuerza mínimos enormes de 1080/900 px que empujaban el teclado fuera de la ventana.

## Archivo modificado

- `app/ui/ventana_principal.py`

## Comprobación realizada

```bash
python3 -m py_compile app/ui/ventana_principal.py app/ui/piano_virtual.py app/ui/pizarra_musical.py
python3 -m compileall app
```
