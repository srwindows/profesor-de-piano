# Cambios v1.7.9 — narración humanizada

- Auditoría de textos del profesor en `app/core/profesor_didactico.py`.
- Corrección de títulos de clase para que terminen en `:` y generen pausa real.
- Revisión de explicaciones, instrucciones, pistas y ejemplos de `data/ejercicios.json`.
- Revisión de `data/lecciones.json` con puntuación y pausas naturales.
- Corrección de la preparación de texto para Piper en `app/voice/voz_avatar.py`:
  - ya no elimina las pausas de los saltos de línea;
  - elimina la numeración de secciones al narrar;
  - añade puntuación a líneas que no la tengan;
  - mantiene pausas tras coma, dos puntos, punto, pregunta y exclamación.
- Pausas por defecto más naturales:
  - coma: 650 ms;
  - punto: 1200 ms.
- Corrección del texto del modo examen en `app/ui/ventana_principal.py`.

Esta versión no incluye voces `.onnx` para mantener el ZIP descargable. Usa las mismas partes de voces entregadas en v1.7.7.
