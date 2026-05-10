# Hotfix Hanon — corrección IndexError al corregir práctica

Este hotfix corrige el fallo:

```text
IndexError: list index out of range
app/core/hanon.py, line 241, in evaluar_eventos
```

## Causa

La evaluación Hanon intentaba leer `eventos[i]` aunque la lista de eventos del alumno fuera más corta que la lista de notas esperadas. Esto pasa si se pulsa **Corregir** antes de completar toda la práctica, si se interrumpe el ejercicio, o si el MIDI no registra todas las notas.

## Corrección aplicada

- `app/core/hanon.py`
  - `evaluar_eventos()` ahora admite prácticas incompletas sin romper el programa.
  - Las notas esperadas no tocadas cuentan como `sin_nota`.
  - Las notas sobrantes cuentan como `nota_extra`.
  - Ya no se accede a índices inexistentes.

- `app/ui/ventana_principal.py`
  - Se evita corregir dos veces el mismo intento Hanon.
  - Se protege la finalización con una bandera interna para evitar dobles llamadas simultáneas.
  - Al iniciar Práctica MIDI o Examen se reinicia correctamente el estado de corrección.

## Comprobación

```bash
python3 -m py_compile app/core/hanon.py app/ui/ventana_principal.py app/ui/pizarra_musical.py app/ui/piano_virtual.py
python3 -m compileall -q app
```

También se ha probado manualmente la evaluación con:

- eventos vacíos;
- práctica parcial;
- práctica completa.

En los tres casos la evaluación devuelve resultado y no lanza `IndexError`.
