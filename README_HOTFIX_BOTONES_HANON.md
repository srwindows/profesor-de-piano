# Hotfix botones internos Hanon

Este hotfix corrige los botones de la pizarra Hanon:

- **Ejemplo**: lanza la demo Hanon real y sincroniza pentagrama, mano y dedo.
- **Piano**: prepara la nota Hanon activa para tocarla, mostrando mano y dedo correcto.
- **Secuencia**: activa una secuencia Hanon real, no una secuencia genérica.
- **Pulso**: activa metrónomo y reto de pulso con la secuencia Hanon.

También se ajusta la pizarra MIDI Didáctico/Hanon para que sus botones usen la nota/secuencia activa del propio MIDI, en lugar de quedarse sin objetivo o caer en un DO genérico.

Archivos modificados:

- `app/ui/pizarra_musical.py`
- `app/ui/ventana_principal.py`

Comprobación realizada:

```bash
python3 -m py_compile app/ui/pizarra_musical.py app/ui/ventana_principal.py
```
