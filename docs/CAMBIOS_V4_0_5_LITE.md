# v4.0.5 — Motor de flujo docente por clase

## Cambio principal

Cada clase del Nivel 0 queda formalmente estructurada:

```text
Clase teórica
↓
Ejercicios asociados
↓
Examen final de clase
↓
Desbloqueo de la siguiente clase
```

La última clase desbloquea el examen global del Nivel 0.

## Archivos añadidos

```text
app/core/flujo_docente.py
data/flujo_docente_nivel_0.json
```

`data/progreso_flujo_docente.json` se crea al ejecutar.

## Integración

- La comprobación pasa a ser examen final de clase.
- El botón de avance sigue bloqueado hasta superar la clase.
- El examen global del Nivel 0 queda asociado a la clase 20.
- El texto del profesor muestra teoría, ejercicios asociados y examen de clase.
