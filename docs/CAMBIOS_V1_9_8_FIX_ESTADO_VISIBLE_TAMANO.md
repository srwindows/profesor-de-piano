# Cambios v1.9.8 FIX — Estado visible y tamaño de arranque

## Problema corregido

En la v1.9.8 el botón **Estado alumno** podía quedar oculto porque la cabecera de estudio tenía demasiados elementos en una sola fila. Además, la ventana arrancaba en `1320x860`, tamaño demasiado grande para pantallas de portátil, especialmente con barra superior del sistema.

## Correcciones

- La ventana ya no arranca a tamaño fijo grande.
- Se calcula el tamaño inicial según la pantalla disponible.
- La ventana se centra automáticamente.
- La cabecera de estudio se ha dividido en:
  - fila de estado;
  - fila de acciones.
- El botón **Estado alumno** queda al principio de la fila de acciones.
- También se añade **Estado alumno** al panel del avatar global para que esté visible aunque la cabecera se estreche.
- Textos de botones compactados:
  - Repasar;
  - Repaso IA;
  - Examen;
  - Plan;
  - Config;
  - Inicio.

## Versión

`APP_VERSION = "1.9.8-FIX-estado-visible-tamano"`

## Nota

ZIP sin carpeta de voces.
