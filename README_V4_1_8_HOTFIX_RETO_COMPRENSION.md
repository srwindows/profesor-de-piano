# Profesor de Piano v4.1.8 Lite — Hotfix Reto de Comprensión

## Ejecutar

```bash
python3 main.py
```

## Corregido

El diálogo de comprensión ya no usa:

```text
QRadioButton.setWordWrap(True)
```

porque ese método no existe en PySide6.

## Prueba

Pulsa un punto superado para abrir el reto de comprensión.
