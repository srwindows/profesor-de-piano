# Cambios v1.8.4 — auditoría de textos y pausas de narración

- Auditoría de los textos didácticos del profesor.
- Cambio de cabecera hablada:
  - `MODO CLASE` se narra separado del título.
  - `Nivel` se narra separado del valor del nivel.
  - `¿Qué vamos a aprender?` se trata como pregunta real.
- Corrección de textos como `Localizar Do, en tu teclado` a `Localizar el Do en tu teclado`.
- Corrección de títulos `Toca Do`, `Toca Re`, etc., a `Toca el Do`, `Toca el Re`, etc., para evitar lecturas unidas como `tocado`.
- La voz ya no destruye saltos de línea: los saltos de línea y párrafos generan pausas reales aunque no haya signos de puntuación.
- Piper ya no recibe cada fragmento con punto final forzado, para evitar lecturas como `inicialo` o `piano virtualo`.
- La pausa y el stop usan bloques de audio más pequeños en sounddevice.
- Se elimina un reinicio interno de estado durante el precalentamiento de voz que podía interferir con la pausa/stop.
- El ZIP sigue sin incluir voces `.onnx`; la carpeta `voices/` debe añadirse manualmente.
