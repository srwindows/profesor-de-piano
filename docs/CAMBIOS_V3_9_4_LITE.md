# v3.9.4 — Pizarra sincronizada con el profesor

## Añadido

El profesor ya no solo lee pasos de la pizarra. Ahora la narración describe exactamente lo que se está dibujando.

## Ejemplo

Si la pizarra está mostrando la clave de Sol, el profesor dice:

```text
Ahora señalo la clave de Sol. Se llama así porque marca la línea donde vive la nota Sol...
```

Si la pizarra avanza a la clave de Fa, el profesor cambia la explicación:

```text
Ahora señalo la clave de Fa. Se llama así porque sus dos puntos señalan la línea donde vive la nota Fa...
```

## Cambios técnicos

- `PizarraMusicalCanvas.texto_narracion_visual_actual()`
- `PizarraMusicalProfesor.texto_sincronizado_actual()`
- `Leer punto actual` ahora abre la pizarra y narra el paso visual inicial.
- Los botones de paso emiten una narración alineada con el dibujo visible.

## Sigue siendo Lite

Sin IA pesada, sin Qwen, sin nube, sin modelos y sin carpeta `voices`.
