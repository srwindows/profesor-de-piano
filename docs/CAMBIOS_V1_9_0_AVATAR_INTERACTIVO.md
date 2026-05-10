# Cambios v1.9.0 — Avatar interactivo e imagen ampliada

## Añadido

- Las imágenes y GIFs de teoría se pueden pulsar.
- Al pulsar una imagen se abre un visor ampliado con explicación del profesor.
- El visor ampliado incluye:
  - imagen/GIF grande;
  - explicación técnica extensa;
  - botón para leer la explicación;
  - botón "Sí, lo he entendido";
  - botón "No, explícamelo otra vez".
- El profesor virtual se involucra más en la clase:
  - explica qué debe mirar el alumno;
  - explica para qué sirve cada concepto;
  - da ejemplos concretos;
  - pregunta si el alumno lo ha entendido;
  - responde a "sí", "no", "ejemplo", "para qué sirve" y "siguiente".
- Se añade una capa local `ProfesorIA.responder_interactivo()` para preparar respuestas pedagógicas en tiempo real sin depender de internet.

## Ajustado

- La pantalla de teoría solo muestra materiales finales, no fotogramas sueltos de construcción.
- Los fotogramas antiguos quedan en la carpeta de assets, pero no se muestran como teoría principal.
- Se mantiene el perfil del alumno guardado en `data/perfil_alumno.json`.
- Se mantiene la carpeta de voces fuera del ZIP.
