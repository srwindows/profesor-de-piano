# Profesor de Piano — v3.7.0 Lite estable

Esta entrega es la base estable y ligera del proyecto.

- Sin IA local pesada.
- Sin modelos incluidos.
- Sin carpeta voices.
- Con profesor/avatar, lectura guiada e interpretación técnica por reglas.
- Pensada para máxima compatibilidad.

Consulta:

```text
README_V3_7_LITE_ESTABLE.md
docs/CAMBIOS_V3_7_0_LITE.md
```

---

# Profesor de Piano IA — v1.9.0

Versión con pantalla de inicio horizontal, teoría visual, avatar global e identificación obligatoria del alumno.

## Novedades v1.9.0

- Al iniciar, antes de la clase, el programa pregunta con quién habla.
- Guarda el perfil en:

```text
data/perfil_alumno.json
```

- El perfil incluye:
  - nombre del alumno;
  - tratamiento masculino, femenino o neutro.
- El avatar queda visible en todas las pantallas.
- El profesor virtual usa el nombre del alumno en sus explicaciones.
- El avatar explica con más detalle para qué sirve cada pantalla, imagen y ejercicio.
- La pantalla de inicio se mantiene horizontal, no como menú vertical.
- La teoría visual carga imágenes y GIF desde:

```text
assets/teoria/nivel_0/
assets/teoria/nivel_0/gifs/
```

- Se mantiene el ZIP sin voces: añade manualmente la carpeta `voices/` en la raíz del proyecto.

## Ejecución

```bash
python3 main.py
```

## Voces Piper

La carpeta `voices/` no va incluida para evitar archivos pesados. Añádela manualmente en la raíz del proyecto.

Rutas recomendadas:

```text
voices/piper/laura/es_MX-laura-high.onnx
voices/piper/es_ES-carlfm-high.onnx
```

## Material visual

El nivel 0 incluye material para:

- mano correcta;
- digitación 1–5;
- GIF de digitación;
- patrón del teclado;
- teclas blancas.

La estructura permite añadir más imágenes, GIFs y vídeos sin tocar el código.


## v1.9.1

Añadida teoría visual de postura al piano y sustituidas imágenes corregidas de patrón del teclado y teclas blancas.

## v1.9.2

Añade lecciones guiadas en JSON, progreso de alumno, preguntas de comprobación y mini evaluación del Nivel 0. El avatar puede leer y explicar cada lección paso a paso.


## v1.9.2 FIX AVANCE

La clase guiada avanza automáticamente tras una respuesta correcta o tras marcar una lección como aprendida.

## v1.9.4

- Mini evaluación final real del Nivel 0.
- Corrección con informe detallado.
- Reintento de preguntas incorrectas.
- Guardado de intentos y estado `nivel_0_superado`.
- Celebración grande al aprobar el Nivel 0.


## v1.9.5

- Mini evaluación Nivel 0 con preguntas en orden aleatorio.
- Respuestas aleatorias en cada pregunta.
- Recalculo automático de la opción correcta tras barajar.
- Respuestas de lecciones guiadas también mezcladas.
- Sin carpeta de voces incluida.


## v1.9.6

Añade práctica interactiva de Nivel 0 con ejercicios de notas y secuencias sobre piano virtual/MIDI.


## v1.9.7

Añadido repaso inteligente con cola de fallos, botón Repaso IA e informe pedagógico en Plan completo.
