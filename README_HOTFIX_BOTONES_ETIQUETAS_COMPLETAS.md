# Hotfix: botones con etiquetas completas

Este hotfix corrige el problema visual por el que muchos botones quedaban demasiado estrechos y no mostraban su etiqueta completa.

## Cambios aplicados

- Los botones principales calculan ahora su ancho mínimo según el texto real.
- Se eliminan los límites máximos pequeños que cortaban etiquetas como `Estado`, `Repaso IA`, `Técnica`, `Sesión`, `Partitura`, etc.
- La fila superior de navegación se coloca dentro de un área horizontal desplazable para que las etiquetas no se aplasten en pantallas pequeñas.
- Los botones de Hanon (`Paso anterior`, `Siguiente paso`, `Práctica MIDI`, etc.) conservan su texto completo.
- Los botones internos de la pizarra musical también tienen ancho mínimo según su etiqueta.
- Los botones de teoría y práctica de Pulso se han ajustado para no quedar cortados.

## Archivos modificados

- `app/ui/ventana_principal.py`
- `app/ui/pizarra_musical.py`
- `app/ui/dialogo_pulso_ritmo.py`
- `app/ui/dialogo_pulso_practica.py`

## Comprobación

Ejecutado:

```bash
python3 -m py_compile app/ui/ventana_principal.py app/ui/pizarra_musical.py app/ui/dialogo_pulso_ritmo.py app/ui/dialogo_pulso_practica.py
python3 -m compileall -q app
```

El ZIP se entrega sin `__pycache__`, sin `.pyc`, sin `.git_checkpoint` y sin carpeta de voces.
