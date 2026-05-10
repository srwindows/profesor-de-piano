# v4.1.8 — Hotfix Reto de Comprensión

## Error corregido

Al pulsar para marcar un punto como superado, se abría `DialogoRetoComprension`
y fallaba porque `QRadioButton` en PySide6 no tiene el método:

```text
setWordWrap
```

Error:

```text
AttributeError: 'PySide6.QtWidgets.QRadioButton' object has no attribute 'setWordWrap'
```

## Archivo corregido

```text
app/ui/dialogo_reto_comprension.py
```

## Solución

- Se elimina `rb.setWordWrap(True)`.
- Se añade un método compatible `_texto_radio_compatible()`.
- El texto largo de la opción se divide manualmente en varias líneas.
- La respuesta real se guarda en `respuesta_original`, para no romper la comparación con la opción correcta.

## Prueba recomendada

1. Ejecutar `python3 main.py`.
2. Pulsar `Leer punto actual`.
3. Pulsar el botón para marcar el punto como superado.
4. Debe abrirse el reto de comprensión sin error.
