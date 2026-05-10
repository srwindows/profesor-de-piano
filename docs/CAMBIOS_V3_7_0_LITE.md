# v3.7.0 — Lite estable

Esta versión vuelve a una base estable y ligera.

## Decisión técnica

Se elimina la IA pesada del centro del programa.

El objetivo ya no es que cada explicación dependa de un modelo local, sino que el curso funcione bien en la mayor cantidad posible de equipos.

## Qué se mantiene

- Pantalla de inicio.
- Profesor/avatar.
- Lectura guiada por puntos.
- Botones de título con lectura correcta.
- Interpretación de textos técnicos por reglas rápidas.
- Partitura.
- Pulso/metrónomo.
- Ruta del curso.
- Estado del alumno.
- Plan personalizado.
- Técnica diaria.
- Sesión diaria.
- Repertorio.
- Piano visible.
- Voz preparada sin incluir carpeta `voices`.

## Qué se evita en esta rama Lite

- Qwen local.
- llama-cpp-python.
- QThread IA.
- Whisper local.
- SmolVLM.
- IA visual.
- Webcam experimental pesada.
- Modelos dentro del ZIP.

## Motivo

Las pruebas han demostrado que la IA local pesada puede volver lento o inestable el programa en algunos equipos.

La rama Lite debe ser el corazón estable para llegar a más usuarios. La IA avanzada queda como módulo opcional futuro, no como dependencia central.
