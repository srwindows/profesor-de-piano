# v4.0.1 — Ajuste visual del pentagrama

## Corregido

En la pizarra musical, el pentagrama inferior quedaba demasiado bajo y podía aparecer cortado.

## Cambio

Se ha subido el sistema de pentagramas dentro del lienzo:

```text
y1: 82 → 58
y2: 170 → 138
```

También se ha reajustado ligeramente la posición del DO central y de las etiquetas para que no invadan la zona inferior.

## Resultado esperado

En `Partitura → Leer punto actual`, el pentagrama inferior debe verse completo.
