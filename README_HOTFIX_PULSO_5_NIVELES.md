# Hotfix Pulso 5 niveles

Se ha convertido la pestaña **Pulso** en un módulo docente real.

## Cambios

- La pestaña Pulso ya no queda vacía.
- Se añaden 25 ejercicios organizados en 5 niveles de progresión:
  1. Pulso básico.
  2. Compás y acento.
  3. Corcheas y subdivisión.
  4. Síncopas y patrones.
  5. Ritmo musical avanzado.
- Cada ejercicio incluye:
  - objetivo didáctico;
  - BPM recomendado;
  - compás;
  - patrón rítmico;
  - instrucciones paso a paso;
  - criterio para superar;
  - texto guía para el profesor.
- Se añade visor visual de patrón rítmico.
- Se añade metrónomo visual y sonoro con:
  - BPM editable;
  - compás editable;
  - sonido activable/desactivable;
  - acento visual en el tiempo 1.
- Se mantiene la integración con el profesor virtual y la lectura guiada por puntos.
- Se conservan los botones esperados por `ventana_principal.py`: leer, marcar completado, práctica, reiniciar y cerrar.

## Archivos modificados

- `data/pulso_ritmo.json`
- `app/ui/dialogo_pulso_ritmo.py`

## Comprobación

```bash
python3 -m py_compile app/ui/dialogo_pulso_ritmo.py app/core/pulso_ritmo.py app/ui/ventana_principal.py
python3 -m compileall -q app
```
